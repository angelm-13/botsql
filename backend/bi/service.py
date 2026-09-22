"""El orquestador: de la pregunta a los datos dibujables.

Es el unico archivo que conoce el flujo completo, y a proposito no conoce a
Flask: recibe objetos y devuelve objetos. Eso permite usar el modulo desde un
script, desde una tarea programada o desde otro framework sin arrastrar el
servidor.

    pregunta
       |
       v  prompt.construir_prompt(esquema en cache)
    modelo (llm_provider)
       |
       v  directive.parsear_directiva   <- el JSON puede venir sucio
    directiva (1..n widgets)
       |
       v  security.validar_sql          <- aqui se cae lo peligroso
       v  executor.ejecutar             <- solo lectura, con reloj y tope
       v  _ajustar_visualizacion        <- los ejes contra las columnas reales
    respuesta

Una decision que vale explicar: un widget que falla NO tumba al dashboard.
El modelo puede acertar cuatro consultas y equivocarse en la quinta; devolver
un error entero en ese caso desperdicia las cuatro que si sirven. Cada widget
lleva su propio `ok` y su propio error.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import date

from bi import directive, prompt as prompt_mod, security
from bi.executor import ejecutar
from bi.llm_provider import ProveedorNoDisponible

# Columnas cuyo nombre sugiere que son el eje de una serie de tiempo.
_PISTAS_DE_TIEMPO = ("fecha", "date", "mes", "month", "dia", "day", "anio",
                     "year", "periodo", "period", "semana", "week", "hora")


@dataclass
class WidgetResuelto:
    ok: bool
    sql: str
    explanation: str
    visualization: dict
    columnas: list[str] = field(default_factory=list)
    filas: list[dict] = field(default_factory=list)
    total_filas: int = 0
    truncado: bool = False
    ms: int = 0
    advertencias: list[str] = field(default_factory=list)
    error: dict | None = None

    def a_dict(self) -> dict:
        salida = {
            "ok": self.ok,
            "sql": self.sql,
            "explanation": self.explanation,
            "visualization": self.visualization,
            "columnas": self.columnas,
            "filas": self.filas,
            "total_filas": self.total_filas,
            "truncado": self.truncado,
            "ms": self.ms,
            "advertencias": self.advertencias,
        }
        if self.error:
            salida["error"] = self.error
        return salida


@dataclass
class RespuestaBI:
    ok: bool
    pregunta: str
    is_dashboard: bool = False
    dashboard_title: str = ""
    widgets: list[WidgetResuelto] = field(default_factory=list)
    error: dict | None = None
    meta: dict = field(default_factory=dict)
    http: int = 200

    def a_dict(self) -> dict:
        salida = {
            "ok": self.ok,
            "pregunta": self.pregunta,
            "is_dashboard": self.is_dashboard,
            "dashboard_title": self.dashboard_title,
            "widgets": [w.a_dict() for w in self.widgets],
            "meta": self.meta,
        }
        if self.error:
            salida["error"] = self.error
        return salida


# ---------------------------------------------------------------------------
# Ajuste de la visualizacion contra los datos reales
# ---------------------------------------------------------------------------

def _es_numerica(filas: list[dict], columna: str) -> bool:
    for fila in filas:
        v = fila.get(columna)
        if v is None:
            continue
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    return False


def _ajustar_visualizacion(vis: directive.Visualizacion, resultado) -> tuple[dict, list[str]]:
    """Corrige los ejes que el modelo invento, contra las columnas que salieron.

    Es el fallo mas frecuente y el mas invisible: el modelo dice
    `y_axis: "total"` y la consulta devolvio la columna como `sum`. Todo
    "funciona" -- hay datos, hay grafica -- y la grafica sale vacia. Como
    aqui ya se tienen las columnas reales, se arregla en vez de devolver un
    dibujo en blanco.
    """
    avisos: list[str] = []
    columnas = list(resultado.columnas)
    filas = resultado.filas
    if not columnas:
        return vis.a_dict(), avisos

    numericas = [c for c in columnas if _es_numerica(filas, c)]
    no_numericas = [c for c in columnas if c not in numericas]

    tipo = vis.chart_type

    # Un solo valor es una tarjeta, aunque el modelo haya pedido barras.
    if len(columnas) == 1 and resultado.total_filas == 1 and tipo not in ("kpi_card", "table"):
        tipo = "kpi_card"
        avisos.append("un solo valor: se dibuja como tarjeta de KPI")

    # Una grafica necesita dos ejes. Sin ellos, la tabla siempre sirve.
    if tipo in ("bar", "line", "pie", "area") and (len(columnas) < 2 or not numericas):
        tipo = "table"
        avisos.append("el resultado no tiene un eje categorico y uno numerico: se muestra como tabla")

    x = vis.x_axis if vis.x_axis in columnas else ""
    y = vis.y_axis if vis.y_axis in columnas else ""

    if tipo in ("bar", "line", "pie", "area"):
        if not x:
            # Para una serie de tiempo el eje es la columna de fecha aunque no
            # sea la primera; para lo demas, la primera no numerica.
            por_tiempo = [c for c in columnas
                          if any(p in c.lower() for p in _PISTAS_DE_TIEMPO)]
            if tipo in ("line", "area") and por_tiempo:
                x = por_tiempo[0]
            else:
                x = no_numericas[0] if no_numericas else columnas[0]
            avisos.append(f"el eje X que propuso el modelo no existe; se usa '{x}'")
        if not y:
            candidatas = [c for c in numericas if c != x]
            y = candidatas[0] if candidatas else (numericas[0] if numericas else columnas[-1])
            avisos.append(f"el eje Y que propuso el modelo no existe; se usa '{y}'")

    if tipo == "kpi_card" and not y:
        y = numericas[0] if numericas else columnas[0]

    salida = vis.a_dict()
    salida["chart_type"] = tipo
    salida["x_axis"] = x
    salida["y_axis"] = y
    if not salida["metric_label"]:
        salida["metric_label"] = y or salida["title"]
    return salida, avisos


# ---------------------------------------------------------------------------
# Resolucion de un widget
# ---------------------------------------------------------------------------

def resolver_widget(w: directive.Widget, esquema, engine, ajustes, gancho=None,
                    relaciones_permitidas=None) -> WidgetResuelto:
    permitidas = relaciones_permitidas if relaciones_permitidas is not None else esquema.nombres

    try:
        validado = security.validar_sql(
            w.sql_query,
            permitidas,
            motor=esquema.motor,
            limite_maximo=ajustes.limite_filas,
            columnas_ocultas=ajustes.columnas_ocultas,
        )
    except security.SqlRechazado as exc:
        return WidgetResuelto(
            ok=False, sql=w.sql_query, explanation=w.explanation,
            visualization=w.visualization.a_dict(),
            error={"tipo": "sql_rechazado", **exc.a_dict()},
        )

    # Que se haya agregado un LIMIT no se avisa: casi toda consulta de KPI
    # devuelve una fila y el aviso solo seria ruido. Lo que si importa -- que
    # el resultado se haya quedado corto -- se dice mas abajo, con el dato ya
    # en la mano.
    avisos: list[str] = []

    try:
        resultado = ejecutar(engine, validado, ajustes=ajustes, gancho=gancho)
    except Exception as exc:
        # El mensaje del motor es lo mas util que hay aqui ("column x does not
        # exist"): se pasa tal cual, recortado. No expone datos, expone el
        # esquema, que este modulo ya le enseno al modelo de todas formas.
        return WidgetResuelto(
            ok=False, sql=validado.sql, explanation=w.explanation,
            visualization=w.visualization.a_dict(), advertencias=avisos,
            error={"tipo": "fallo_de_ejecucion", "mensaje": str(exc)[:500]},
        )

    vis, avisos_vis = _ajustar_visualizacion(w.visualization, resultado)
    if resultado.truncado:
        avisos.append(f"la consulta devolvio mas de {ajustes.limite_filas} filas; se recortaron")

    return WidgetResuelto(
        ok=True,
        sql=validado.sql,
        explanation=w.explanation,
        visualization=vis,
        columnas=list(resultado.columnas),
        filas=resultado.filas,
        total_filas=resultado.total_filas,
        truncado=resultado.truncado,
        ms=resultado.ms,
        advertencias=avisos + avisos_vis,
    )


# ---------------------------------------------------------------------------
# El flujo completo
# ---------------------------------------------------------------------------

def responder(
    pregunta: str,
    *,
    engine,
    proveedor,
    ajustes,
    cache_esquema,
    hoy: date | None = None,
    gancho=None,
    relaciones_permitidas=None,
) -> RespuestaBI:
    """Contesta una pregunta de punta a punta."""
    inicio = time.monotonic()
    pregunta = (pregunta or "").strip()

    if not pregunta:
        return RespuestaBI(ok=False, pregunta="", http=400,
                           error={"tipo": "peticion_invalida",
                                  "mensaje": "Falta el campo 'prompt'."})

    esquema = cache_esquema.obtener()
    if not esquema.relaciones:
        return RespuestaBI(ok=False, pregunta=pregunta, http=503,
                           error={"tipo": "esquema_vacio",
                                  "mensaje": "No hay ninguna tabla consultable. "
                                             "Revise BI_INCLUDE_TABLES / BI_EXCLUDE_TABLES."})

    texto_prompt = prompt_mod.construir_prompt(
        pregunta, esquema,
        limite_filas=ajustes.limite_filas,
        hoy=hoy,
        max_widgets=ajustes.max_widgets,
    )

    try:
        salida = proveedor.generar(texto_prompt, pregunta)
    except ProveedorNoDisponible as exc:
        return RespuestaBI(ok=False, pregunta=pregunta, http=503,
                           error={"tipo": "modelo_no_disponible", "mensaje": str(exc)})

    meta = {
        "modelo": salida.modelo,
        "ms_modelo": salida.ms,
        "tokens_prompt": salida.tokens_prompt,
        "tokens_respuesta": salida.tokens_respuesta,
        "motor": esquema.motor,
        "huella_esquema": esquema.huella,
        "relaciones_expuestas": len(esquema.relaciones),
    }

    try:
        dir_ = directive.parsear_directiva(salida.texto, max_widgets=ajustes.max_widgets)
    except directive.DirectivaInvalida as exc:
        meta["ms_total"] = int((time.monotonic() - inicio) * 1000)
        return RespuestaBI(
            ok=False, pregunta=pregunta, http=502, meta=meta,
            error={"tipo": "directiva_invalida", "motivo": exc.motivo,
                   "mensaje": "El modelo no devolvio el JSON del contrato.",
                   "respuesta_cruda": exc.crudo},
        )

    if dir_.rechazada_por_el_modelo:
        meta["ms_total"] = int((time.monotonic() - inicio) * 1000)
        return RespuestaBI(
            ok=False, pregunta=pregunta, http=403, meta=meta,
            error={"tipo": "rechazada_por_el_modelo", "mensaje": dir_.error},
        )

    resueltos = [
        resolver_widget(w, esquema, engine, ajustes, gancho, relaciones_permitidas)
        for w in dir_.widgets
    ]

    meta["ms_total"] = int((time.monotonic() - inicio) * 1000)
    alguno_ok = any(w.ok for w in resueltos)

    respuesta = RespuestaBI(
        ok=alguno_ok,
        pregunta=pregunta,
        is_dashboard=dir_.is_dashboard,
        dashboard_title=dir_.dashboard_title,
        widgets=resueltos,
        meta=meta,
        http=200 if alguno_ok else 422,
    )
    if not alguno_ok:
        primero = resueltos[0].error if resueltos else None
        respuesta.error = {
            "tipo": "ninguna_consulta_ejecutable",
            "mensaje": "Ninguna de las consultas generadas paso la validacion o se pudo ejecutar.",
            "detalle": primero,
        }
    return respuesta
