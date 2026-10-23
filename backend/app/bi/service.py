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

import logging
import re
import threading
import time
from dataclasses import dataclass, field, replace
from datetime import date

from . import auditor, busqueda, conocimiento, directive, ejemplos as banco_ej, prediccion, prompt as prompt_mod, recetas, security
from .acceso import acotar_sql
from .executor import ejecutar
from .llm_provider import ProveedorNoDisponible, RespuestaLLM, _normalizar

_log = logging.getLogger(__name__)
_audit = logging.getLogger("bi.audit")

# Columnas cuyo nombre sugiere que son el eje de una serie de tiempo.
_PISTAS_DE_TIEMPO = ("fecha", "date", "mes", "month", "dia", "day", "anio",
                     "year", "periodo", "period", "semana", "week", "hora")


# ---------------------------------------------------------------------------
# Cache de preguntas
# ---------------------------------------------------------------------------

class CacheDePreguntas:
    """Guarda el JSON crudo que devolvio el modelo, para reusarlo en preguntas
    repetidas -- exactas, no parecidas.

    Es lo que mas pesa en el reloj: pensar el SQL le cuesta al modelo entre
    45 y 100 segundos (ver llm_provider.py), y una demostracion repite las
    mismas preguntas de ejemplo una y otra vez. Se cachea el TEXTO del
    modelo, nunca las filas de la consulta: el SQL se vuelve a validar y a
    ejecutar siempre, en vivo, con el `gancho`/`relaciones_permitidas` de
    ESA peticion -- asi el dato nunca sale viejo ni se filtra de un
    inquilino a otro cuando dos usuarios con alcances distintos hacen la
    misma pregunta. Solo se ahorra la parte cara, que es traducir a SQL, no
    la parte sensible, que es leer datos.

    La clave incluye la huella del esquema: si el esquema cambia (se agrega
    una tabla, cambia una columna), una respuesta vieja para la misma
    pregunta ya no aplica y se recalcula sola, sin necesidad de invalidar
    nada a mano.
    """

    def __init__(self, ttl_s: int = 3600):
        self.ttl_s = ttl_s
        self._entradas: dict[str, tuple[str, str, float]] = {}
        self._lock = threading.Lock()
        self.aciertos = 0
        self.fallos = 0

    @staticmethod
    def _clave(pregunta: str, huella_esquema: str) -> str:
        return f"{huella_esquema}|{_normalizar(pregunta.strip())}"

    def obtener(self, pregunta: str, huella_esquema: str) -> tuple[str, str] | None:
        if self.ttl_s <= 0:
            return None
        clave = self._clave(pregunta, huella_esquema)
        ahora = time.time()
        with self._lock:
            entrada = self._entradas.get(clave)
            if entrada is None or ahora >= entrada[2]:
                self.fallos += 1
                return None
            self.aciertos += 1
            return entrada[0], entrada[1]

    def guardar(self, pregunta: str, huella_esquema: str, texto: str, modelo: str) -> None:
        if self.ttl_s <= 0:
            return
        clave = self._clave(pregunta, huella_esquema)
        with self._lock:
            self._entradas[clave] = (texto, modelo, time.time() + self.ttl_s)

    def invalidar(self) -> None:
        with self._lock:
            self._entradas.clear()

    @property
    def estado(self) -> dict:
        return {"aciertos": self.aciertos, "fallos": self.fallos,
                "entradas": len(self._entradas), "ttl_s": self.ttl_s}


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
    # El SQL se queda en el servidor (log/auditoria). Solo sale al cliente si
    # quien pregunta es administrador y lo pidio explicitamente.
    exponer_sql: bool = False
    reparada: bool = False       # el SQL del modelo se corrigio solo (no sirve de ejemplo)

    def a_dict(self) -> dict:
        salida = {
            "ok": self.ok,
            "explanation": self.explanation,
            "visualization": self.visualization,
            "columnas": self.columnas,
            "filas": self.filas,
            "total_filas": self.total_filas,
            "truncado": self.truncado,
            "ms": self.ms,
            "advertencias": self.advertencias,
        }
        if self.exponer_sql:
            salida["sql"] = self.sql
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

# ---------------------------------------------------------------------------
# Graficas solo si se piden
# ---------------------------------------------------------------------------

_TIPOS_DE_GRAFICA = ("bar", "line", "pie", "area")
_PIDE_GRAFICA = re.compile(
    r'(?i)\b(grafic|chart|diagrama|barras?|pastel|torta|dona|histograma|tendencia|dashboard|tablero)')
_PIDE_TIPO = (
    (re.compile(r'(?i)\b(pastel|torta|dona|pie)\b'), 'pie'),
    (re.compile(r'(?i)\b(lineas?|tendencia|evolucion)\b'), 'line'),
    (re.compile(r'(?i)\b(area)\b'), 'area'),
    (re.compile(r'(?i)\b(barras?|columnas?)\b'), 'bar'),
)


def grafica_pedida(pregunta: str) -> str | None:
    """None = el usuario NO pidio grafica (se muestra tabla); "auto" = pidio
    grafica sin decir de que tipo; o el tipo concreto (bar, line, pie, area)."""
    import unicodedata
    texto = "".join(c for c in unicodedata.normalize("NFKD", pregunta or "")
                    if not unicodedata.combining(c))
    if not _PIDE_GRAFICA.search(texto):
        return None
    for patron, tipo in _PIDE_TIPO:
        if patron.search(texto):
            return tipo
    return "auto"


def _aplicar_preferencia_de_grafica(vis: dict, resultado, grafica: str | None) -> None:
    """Tabla por omision; grafica solo si la pregunta la pidio. Una tarjeta de
    un solo valor (KPI) no es una grafica y se respeta."""
    tipo = vis.get("chart_type")
    if tipo in ("kpi_card",):
        return
    if grafica is None:
        if tipo in _TIPOS_DE_GRAFICA:
            vis["chart_type"] = "table"
        return
    if grafica in _TIPOS_DE_GRAFICA and tipo != grafica:
        columnas = list(resultado.columnas)
        numericas = [c for c in columnas if _es_numerica(resultado.filas, c)]
        if len(columnas) >= 2 and numericas:
            vis["chart_type"] = grafica
            if vis.get("x_axis") not in columnas:
                vis["x_axis"] = next((c for c in columnas if c not in numericas), columnas[0])
            if vis.get("y_axis") not in columnas:
                vis["y_axis"] = numericas[0]
    elif grafica == "auto" and tipo == "table":
        columnas = list(resultado.columnas)
        numericas = [c for c in columnas if _es_numerica(resultado.filas, c)]
        if len(columnas) >= 2 and numericas and resultado.total_filas > 1:
            vis["chart_type"] = "bar"
            vis["x_axis"] = next((c for c in columnas if c not in numericas), columnas[0])
            vis["y_axis"] = numericas[0]


_USER_SIN_COMILLAS = re.compile(r'(?i)\b(from|join)\s+user\b(?!\s*\.)|(?<!")\buser\.(?=\w)')


def _arreglar_user(sql: str) -> str:
    """`user` sin comillas es una palabra reservada de PostgreSQL (devuelve el
    usuario de la sesion, no la tabla), y el modelo chico la escribe asi casi
    siempre. Se cita aqui, de forma determinista, en vez de confiar en el prompt."""
    def _sub(m):
        return f'{m.group(1)} "user"' if m.group(1) else '"user".'
    return _USER_SIN_COMILLAS.sub(_sub, sql)


# Alias de tabla que son palabras reservadas (el modelo chico escribe `JOIN inventory_stock is`).
_ALIAS_RESERVADO = re.compile(
    r'(?i)\b(from|join)\s+((?:"?\w+"?\.)?"?\w+"?)\s+(?:as\s+)?(is|in|or|to|do|on|as|and|not|all|any|end|for|if|case|check|desc|asc|table|select|with|by|at|no|of)\b(?!\s*[(,])'
)


def _arreglar_alias(sql: str) -> str:
    """Renombra un alias reservado (`is`, `in`, `or`...) a `t_<alias>` en toda la consulta."""
    renombrados = {}

    def _decl(m):
        alias = m.group(3)
        renombrados[alias.lower()] = f't_{alias.lower()}'
        return f'{m.group(1)} {m.group(2)} t_{alias.lower()}'

    nuevo = _ALIAS_RESERVADO.sub(_decl, sql)
    for viejo, nombre in renombrados.items():
        nuevo = re.sub(r'(?i)(?<![\w"])' + viejo + r'(?=\.)', nombre, nuevo)
    return nuevo


# ---------------------------------------------------------------------------
# Reparacion de consultas que el motor rechaza
# ---------------------------------------------------------------------------

# El modelo chico dice product_name donde la columna se llama descripcion. Postgres
# casi siempre sugiere la correcta (HINT); cuando no, se busca la mas parecida o un
# equivalente de negocio entre las columnas REALES de las tablas de la consulta.
_EQUIVALENTES = {
    "name": ("name", "full_name", "descripcion", "description"),
    "nombre": ("name", "full_name", "descripcion", "description"),
    "product_name": ("descripcion",),
    "producto": ("descripcion",),
    "description": ("descripcion", "title", "note"),
    "price": ("gross_price", "total", "amount"),
    "precio": ("gross_price", "total", "amount"),
    "quantity": ("cantidad", "quantity"),
    "stock": ("cantidad", "quantity"),
    "existencias": ("cantidad", "quantity"),
    "status": ("incident_status", "proyect_status", "invoice_status", "product_status", "sale_status", "id_status"),
    "estatus": ("incident_status", "proyect_status", "invoice_status", "product_status", "sale_status", "id_status"),
    "created_at": ("creation_date",),
    "date": ("date_emision", "incident_date", "creation_date", "date"),
    "fecha": ("date_emision", "incident_date", "creation_date", "date"),
    "code": ("product_code", "task_code", "folio"),
    "sku": ("product_code",),
    "customer": ("id_customer_supplier",),
    "total_amount": ("total",),
    "amount": ("amount", "total"),
}
_COL_NO_EXISTE = re.compile(r'column (?:"?([A-Za-z_]\w*)"?\.)?"?([A-Za-z_]\w*)"? does not exist')
_HINT = re.compile(r'Perhaps you meant to reference the column "?(\w+)"?\."?(\w+)"?')


def _tablas_de_la_consulta(sql: str, esquema) -> dict:
    """alias -> columnas reales, para cada tabla que la consulta nombra."""
    por_nombre = {r.nombre.lower(): [c.nombre for c in r.columnas] for r in esquema.relaciones}
    salida = {}
    patron = re.compile(r'(?i)\b(?:from|join)\s+"?(\w+)"?(?:\s+(?:as\s+)?"?(\w+)"?)?')
    for m in patron.finditer(sql):
        tabla, alias = m.group(1).lower(), (m.group(2) or "").lower()
        if tabla in por_nombre:
            salida[tabla] = por_nombre[tabla]
            if alias and alias not in ("on", "where", "group", "order", "join", "left", "inner", "limit"):
                salida[alias] = por_nombre[tabla]
    return salida


def _reparar_sql(sql: str, error: str, esquema):
    """Una version corregida de `sql`, o None si no hay forma segura de arreglarla."""
    m = _COL_NO_EXISTE.search(error or "")
    if not m:
        return None
    calif, col = (m.group(1) or ""), m.group(2)
    h = _HINT.search(error or "")
    if h:
        nuevo_col = h.group(2)
    else:
        tablas = _tablas_de_la_consulta(sql, esquema)
        candidatas = tablas.get(calif.lower()) if calif else None
        if candidatas is None:
            candidatas = sorted({c for cols in tablas.values() for c in cols})
        bajas = {c.lower(): c for c in candidatas}
        nuevo_col = None
        for equiv in _EQUIVALENTES.get(col.lower(), ()):
            if equiv in bajas:
                nuevo_col = bajas[equiv]
                break
        if nuevo_col is None:
            import difflib
            parecidas = difflib.get_close_matches(col.lower(), list(bajas), n=1, cutoff=0.6)
            nuevo_col = bajas[parecidas[0]] if parecidas else None
    if not nuevo_col or nuevo_col.lower() == col.lower():
        return None
    objetivo = (calif + "." if calif else "") + col
    reemplazo = (calif + "." if calif else "") + nuevo_col
    nuevo = re.sub(r'(?<![\w."])' + re.escape(objetivo) + r'(?![\w"])', reemplazo, sql)
    return nuevo if nuevo != sql else None


def resolver_widget(w: directive.Widget, esquema, engine, ajustes, gancho=None,
                    relaciones_permitidas=None, columnas_negadas=frozenset(),
                    exponer_sql: bool = False, existentes=None,
                    grafica: str | None = None, acceso=None) -> WidgetResuelto:
    permitidas = relaciones_permitidas if relaciones_permitidas is not None else esquema.nombres
    ocultas = tuple(ajustes.columnas_ocultas) + tuple(sorted(columnas_negadas))
    w.sql_query = _arreglar_alias(_arreglar_user(w.sql_query))

    avisos: list[str] = []
    validado = resultado = None
    reparada = False
    for intento in range(3):
        try:
            validado = security.validar_sql(
                w.sql_query,
                permitidas,
                motor=esquema.motor,
                limite_maximo=ajustes.limite_filas,
                columnas_ocultas=ocultas,
            )
            validado = replace(validado, sql=acotar_sql(validado.sql, acceso, esquema))
        except security.SqlRechazado as exc:
            _log.warning("BI sql rechazado (%s): %s", exc.a_dict().get("motivo"), w.sql_query[:300])
            detalle = exc.a_dict()
            if not exponer_sql and detalle.get("motivo") == "relacion_no_permitida" and existentes is not None \
                    and not any(r.split(".")[-1] in existentes for r in security.relaciones_referenciadas(w.sql_query)):
                # La tabla no esta vedada: sencillamente no existe (el modelo la invento).
                detalle = {"motivo": "no_encontrado",
                           "mensaje": "No encontre datos para esa parte de la pregunta. Intenta reformularla con otros terminos."}
            elif not exponer_sql:
                # El motivo ("columna_sensible", "relacion_no_permitida") basta; el
                # detalle puede nombrar tablas o columnas que este rol no debe ni
                # saber que existen.
                detalle = {"motivo": detalle.get("motivo"),
                           "mensaje": "La consulta no esta permitida para tu rol."}
            return WidgetResuelto(
                ok=False, sql=w.sql_query, explanation=w.explanation,
                visualization=w.visualization.a_dict(), exponer_sql=exponer_sql,
                error={"tipo": "sql_rechazado", **detalle},
            )
        try:
            resultado = ejecutar(engine, validado, ajustes=ajustes, gancho=gancho)
            break
        except Exception as exc:
            _log.warning("BI fallo de ejecucion (intento %d): %s | %s", intento + 1, str(exc)[:300], validado.sql[:300])
            # Se intenta arreglar solo (columna mal nombrada); el SQL nuevo vuelve a
            # pasar por el validador completo, asi que la reparacion no abre nada.
            nuevo = _reparar_sql(w.sql_query, str(getattr(exc, "orig", exc)), esquema) if intento < 2 else None
            if nuevo:
                _log.info("BI consulta reparada: %s", nuevo[:300])
                w.sql_query = nuevo
                reparada = True
                continue
            return WidgetResuelto(
                ok=False, sql=validado.sql, explanation=w.explanation,
                visualization=w.visualization.a_dict(), advertencias=avisos,
                exponer_sql=exponer_sql,
                error={"tipo": "fallo_de_ejecucion",
                       "mensaje": (str(exc)[:500] if exponer_sql else
                                   "No se pudo ejecutar la consulta. Reformula la pregunta.")},
            )

    # Defensa en profundidad: un `SELECT *` no nombra columnas, asi que el
    # validador no las vio. Lo que el rol no puede leer se quita del resultado.
    if columnas_negadas:
        quitar = {c for c in resultado.columnas if c.lower() in columnas_negadas}
        if quitar:
            resultado.columnas = tuple(c for c in resultado.columnas if c not in quitar)
            resultado.filas = [{k: v for k, v in f.items() if k not in quitar}
                               for f in resultado.filas]

    vis, avisos_vis = _ajustar_visualizacion(w.visualization, resultado)
    _aplicar_preferencia_de_grafica(vis, resultado, grafica)
    if resultado.truncado:
        avisos.append(f"la consulta devolvio mas de {ajustes.limite_filas} filas; se recortaron")

    return WidgetResuelto(
        ok=True,
        reparada=reparada,
        exponer_sql=exponer_sql,
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
    cache_preguntas: CacheDePreguntas | None = None,
    id_department: int | None = None,
    acceso=None,
    exponer_sql: bool = False,
    usuario: dict | None = None,
) -> RespuestaBI:
    """Contesta una pregunta de punta a punta.

    `acceso` (ver acceso.py) limita tablas y columnas al rol del usuario; sin
    el, se ve todo lo que el extractor exponga. Cada pregunta deja una linea
    de auditoria en el logger "bi.audit".
    """
    r = _responder(pregunta, engine=engine, proveedor=proveedor, ajustes=ajustes,
                   cache_esquema=cache_esquema, gancho=gancho,
                   relaciones_permitidas=relaciones_permitidas,
                   cache_preguntas=cache_preguntas, hoy=hoy, id_department=id_department,
                   acceso=acceso, exponer_sql=exponer_sql)
    _auditar(pregunta, r, acceso, usuario)
    auditor.auditar_en_segundo_plano(proveedor, pregunta, acceso, usuario, [w.sql for w in r.widgets if w.ok])
    return r


def _auditar(pregunta, r, acceso, usuario) -> None:
    import json as _json
    usuario = usuario or {}
    _audit.info(_json.dumps({
        "usuario": usuario.get("id_user") or usuario.get("sub") or usuario.get("username"),
        "rol": getattr(acceso, "rol", None),
        "admin": getattr(acceso, "es_admin", None),
        "pregunta": pregunta[:300],
        "ok": r.ok, "http": r.http,
        "error": (r.error or {}).get("tipo"),
        "widgets": [{"ok": w.ok, "ms": w.ms, "filas": w.total_filas,
                     "sql": w.sql[:500]} for w in r.widgets],
        "ms_modelo": r.meta.get("ms_modelo"), "ms_total": r.meta.get("ms_total"),
        "desde_cache": r.meta.get("desde_cache"),
    }, ensure_ascii=False))


def _widget_manual(titulo, explicacion, columnas, filas, tipo="table", x="", y="", avisos=None, ms=0,
                   exponer_sql=False, sql=""):
    return WidgetResuelto(
        ok=True, sql=sql, explanation=explicacion, exponer_sql=exponer_sql,
        visualization={"chart_type": tipo, "title": titulo, "x_axis": x, "y_axis": y,
                       "metric_label": y or titulo, "recommended": True},
        columnas=list(columnas), filas=filas, total_filas=len(filas), ms=ms, advertencias=avisos or [],
    )


def _responder_prediccion(pregunta, *, esquema, engine, ajustes, gancho, relaciones_permitidas, acceso,
                          existentes, exponer_sql, inicio) -> RespuestaBI:
    """Pronostico estadistico (ver prediccion.py) sobre una serie mensual real."""
    serie = prediccion.serie_para(pregunta)
    if serie is None:
        w = _widget_manual(
            "Analisis predictivo", "Puedo pronosticar series mensuales de: vales (incidencias), herramientas "
            "prestadas, facturacion y ventas del punto de venta. Por ejemplo: \"predice los vales de los "
            "proximos 3 meses\" o \"pronostico de facturacion\".", [], [], tipo="text")
        return RespuestaBI(ok=True, pregunta=pregunta, widgets=[w], http=200,
                           meta={"modelo": "prediccion", "ms_modelo": 0, "tipo": "prediccion",
                                 "ms_total": int((time.monotonic() - inicio) * 1000)})
    titulo, unidad, sql = serie
    base = resolver_widget(
        directive.Widget(sql_query=sql, explanation=titulo, visualization=directive.Visualizacion(chart_type="table", title=titulo)),
        esquema, engine, ajustes, gancho, relaciones_permitidas,
        columnas_negadas=(acceso.columnas_negadas if acceso else frozenset()),
        exponer_sql=exponer_sql, existentes=existentes, grafica=None, acceso=acceso)
    if not base.ok:
        base.visualization = {"chart_type": "table", "title": titulo}
        return RespuestaBI(ok=False, pregunta=pregunta, widgets=[base], http=422,
                           error={"tipo": "ninguna_consulta_ejecutable",
                                  "mensaje": "No se pudo obtener la serie historica para pronosticar."},
                           meta={"modelo": "prediccion", "ms_modelo": 0,
                                 "ms_total": int((time.monotonic() - inicio) * 1000)})
    pasos = prediccion.horizonte(pregunta)
    filas, explicacion, avisos = prediccion.construir_tabla(base.filas, pasos, unidad)
    if filas is None:
        w = _widget_manual(titulo, explicacion, [], [], tipo="text")
    else:
        pide = grafica_pedida(pregunta)
        w = _widget_manual("Pronostico: " + titulo, explicacion, ["mes", "valor", "tipo", "minimo", "maximo"], filas,
                           tipo=("line" if pide else "table"), x="mes", y="valor", avisos=avisos, ms=base.ms,
                           exponer_sql=exponer_sql, sql=sql)
    return RespuestaBI(ok=True, pregunta=pregunta, widgets=[w], http=200,
                       meta={"modelo": "prediccion", "ms_modelo": 0, "tipo": "prediccion",
                             "ms_total": int((time.monotonic() - inicio) * 1000)})


def _responder_busqueda(pregunta, termino, *, esquema, engine, ajustes, gancho, relaciones_permitidas, acceso,
                        existentes, exponer_sql, inicio) -> RespuestaBI:
    """Busca el termino en todas las tablas/columnas de texto que el rol puede leer."""
    dueno = {}
    try:
        from app.modules.registry import MODULOS
        dueno = {e: m.etiqueta for m in MODULOS for e in m.entidades}
    except Exception:
        pass
    filas, vistos, ms_total = [], set(), 0
    for sql in busqueda.sentencias(esquema, termino):
        w = resolver_widget(
            directive.Widget(sql_query=sql, explanation="", visualization=directive.Visualizacion(chart_type="table", title="Busqueda")),
            esquema, engine, ajustes, gancho, relaciones_permitidas,
            columnas_negadas=(acceso.columnas_negadas if acceso else frozenset()),
            exponer_sql=False, existentes=existentes, grafica=None, acceso=acceso)
        if not w.ok:
            _log.warning("BI busqueda: un bloque fallo: %s", (w.error or {}).get("motivo") or (w.error or {}).get("tipo"))
            continue
        ms_total += w.ms
        for f in w.filas:
            clave = (f.get("tabla"), f.get("campo"), f.get("llave"))
            if clave in vistos:
                continue
            vistos.add(clave)
            filas.append({"modulo": dueno.get(str(f.get("tabla")).lower(), "otras pantallas"),
                          "tabla": f.get("tabla"), "campo": f.get("campo"),
                          "valor": str(f.get("valor"))[:160], "llave": f.get("llave")})
        if len(filas) >= busqueda.MAX_FILAS:
            break
    filas = filas[:busqueda.MAX_FILAS]
    tablas = len({f["tabla"] for f in filas})
    expl = (f"{len(filas)} coincidencias de \"{termino}\" en {tablas} tablas que tu rol puede leer."
            if filas else f"No encontre \"{termino}\" en las tablas que tu rol puede leer.")
    w = _widget_manual(f"Resultados de \"{termino}\"", expl, ["modulo", "tabla", "campo", "valor", "llave"], filas,
                       ms=ms_total, avisos=(["Resultado recortado a %d filas." % busqueda.MAX_FILAS]
                                            if len(filas) >= busqueda.MAX_FILAS else []))
    return RespuestaBI(ok=True, pregunta=pregunta, widgets=[w], http=200,
                       meta={"modelo": "busqueda", "ms_modelo": 0, "tipo": "busqueda",
                             "ms_total": int((time.monotonic() - inicio) * 1000)})


def _responder_con_documentacion(pregunta, *, proveedor, cache_preguntas, acceso, cache_esquema,
                                 id_department, inicio) -> RespuestaBI:
    """Responde con texto a partir de la documentacion del sistema."""
    import json as _json

    try:
        esquema = cache_esquema.obtener(id_department=id_department, acceso=acceso)
    except Exception:
        esquema = None
    trozos = conocimiento.buscar(pregunta, acceso, esquema)
    huella = f"kb|{getattr(acceso, 'clave', 'anon')}|" + "|".join(f.titulo for f in trozos)
    cacheado = cache_preguntas.obtener(pregunta, huella) if cache_preguntas else None
    desde_cache = cacheado is not None
    if cacheado is not None:
        texto, modelo = cacheado[0], cacheado[1] + " (cache)"
        ms_modelo = 0
    else:
        if not trozos:
            texto, modelo, ms_modelo = _json.dumps({"respuesta": "No encontre eso en la documentacion a la que tu rol tiene acceso."}), "sin-documentacion", 0
        else:
            try:
                salida = proveedor.generar(conocimiento.construir_prompt(pregunta, trozos), pregunta,
                                           formato=conocimiento.ESQUEMA_TEXTO)
            except ProveedorNoDisponible as exc:
                return RespuestaBI(ok=False, pregunta=pregunta, http=503,
                                   error={"tipo": "modelo_no_disponible", "mensaje": str(exc)})
            texto, modelo, ms_modelo = salida.texto, salida.modelo, salida.ms
            if cache_preguntas is not None:
                cache_preguntas.guardar(pregunta, huella, texto, modelo)
    try:
        respuesta = str(_json.loads(texto).get("respuesta") or "").strip()
    except (ValueError, AttributeError):
        respuesta = ""
    if not respuesta:
        respuesta = "No encontre eso en la documentacion a la que tu rol tiene acceso."
    widget = WidgetResuelto(
        ok=True, sql="", explanation=respuesta,
        visualization={"chart_type": "text", "title": "Respuesta", "recommended": True,
                       "fuentes": sorted({f.titulo for f in trozos})[:4]},
    )
    meta = {"modelo": modelo, "ms_modelo": ms_modelo, "tipo": "documentacion",
            "desde_cache": desde_cache, "ms_total": int((time.monotonic() - inicio) * 1000)}
    return RespuestaBI(ok=True, pregunta=pregunta, widgets=[widget], meta=meta, http=200)


def _responder(
    pregunta: str,
    *,
    engine,
    proveedor,
    ajustes,
    cache_esquema,
    gancho=None,
    relaciones_permitidas=None,
    cache_preguntas=None,
    hoy=None,
    id_department=None,
    acceso=None,
    exponer_sql: bool = False,
) -> RespuestaBI:
    inicio = time.monotonic()
    pregunta = (pregunta or "").strip()

    if not pregunta:
        return RespuestaBI(ok=False, pregunta="", http=400,
                           error={"tipo": "peticion_invalida",
                                  "mensaje": "Falta el campo 'prompt'."})

    # Preguntas del sistema (que es un vale, que modulos hay...): no son datos, se
    # contestan con la documentacion y no con SQL.
    if conocimiento.es_pregunta_de_sistema(pregunta):
        return _responder_con_documentacion(
            pregunta, proveedor=proveedor, cache_preguntas=cache_preguntas, acceso=acceso,
            cache_esquema=cache_esquema, id_department=id_department, inicio=inicio)

    esquema = cache_esquema.obtener(id_department=id_department, acceso=acceso)
    if not esquema.relaciones:
        return RespuestaBI(ok=False, pregunta=pregunta, http=503,
                           error={"tipo": "esquema_vacio",
                                  "mensaje": "No hay ninguna tabla consultable. "
                                             "Revise BI_INCLUDE_TABLES / BI_EXCLUDE_TABLES."})

    # Pronostico y busqueda global los resuelve codigo, no el modelo de lenguaje.
    comunes = dict(esquema=esquema, engine=engine, ajustes=ajustes, gancho=gancho,
                   relaciones_permitidas=relaciones_permitidas, acceso=acceso,
                   existentes=(cache_esquema.obtener().nombres if acceso is not None and not acceso.es_admin else None),
                   exponer_sql=exponer_sql, inicio=inicio)
    if prediccion.es_prediccion(pregunta):
        return _responder_prediccion(pregunta, **comunes)
    termino = busqueda.detectar(pregunta)
    if termino and recetas.buscar(pregunta) is None:
        return _responder_busqueda(pregunta, termino, **comunes)

    similares = banco_ej.buscar(pregunta, acceso)
    bloque_ej = banco_ej.formatear(similares, pregunta) if similares else ""
    texto_prompt = prompt_mod.construir_prompt(
        pregunta, esquema,
        ejemplos=bloque_ej,
        limite_filas=ajustes.limite_filas,
        hoy=hoy,
        max_widgets=ajustes.max_widgets,
    )

    desde_cache = False
    receta = recetas.buscar(pregunta)
    cacheado = (cache_preguntas.obtener(pregunta, esquema.huella)
                if (cache_preguntas and receta is None) else None)
    if receta is not None:
        # Pregunta frecuente con SQL ya verificado: no se gasta el modelo.
        salida = RespuestaLLM(texto=receta, modelo="receta", ms=0)
    elif cacheado is not None:
        texto_cache, modelo_cache = cacheado
        salida = RespuestaLLM(texto=texto_cache, modelo=f"{modelo_cache} (cache)", ms=0)
        desde_cache = True
    else:
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
        "desde_cache": desde_cache,
    }

    try:
        dir_ = directive.parsear_directiva(salida.texto, max_widgets=ajustes.max_widgets)
    except directive.DirectivaInvalida as exc:
        meta["ms_total"] = int((time.monotonic() - inicio) * 1000)
        return RespuestaBI(
            ok=False, pregunta=pregunta, http=502, meta=meta,
            error={"tipo": "directiva_invalida", "motivo": exc.motivo,
                   "mensaje": "El modelo no devolvio el JSON del contrato.",
                   **({"respuesta_cruda": exc.crudo} if exponer_sql else {})},
        )

    if dir_.rechazada_por_el_modelo:
        meta["ms_total"] = int((time.monotonic() - inicio) * 1000)
        return RespuestaBI(
            ok=False, pregunta=pregunta, http=403, meta=meta,
            error={"tipo": "rechazada_por_el_modelo", "mensaje": dir_.error},
        )

    # Para distinguir "no tienes permiso" de "esa tabla no existe".
    existentes = (cache_esquema.obtener().nombres if acceso is not None and not acceso.es_admin else None)
    resueltos = [
        resolver_widget(w, esquema, engine, ajustes, gancho, relaciones_permitidas,
                        columnas_negadas=(acceso.columnas_negadas if acceso else frozenset()),
                        exponer_sql=exponer_sql, existentes=existentes,
                        grafica=grafica_pedida(pregunta), acceso=acceso)
        for w in dir_.widgets
    ]

    # Solo se recuerda lo que funciono: guardar el SQL antes de ejecutarlo hacia que
    # una consulta mala se repitiera una hora entera.
    if (cache_preguntas is not None and not desde_cache and receta is None
            and not dir_.rechazada_por_el_modelo and resueltos and all(w.ok for w in resueltos)):
        # El nombre del modelo real, no el que ya trae "(cache)" encima --
        # asi una segunda pregunta identica etiqueta bien de que modelo salio.
        cache_preguntas.guardar(pregunta, esquema.huella, salida.texto, salida.modelo)

    meta["ms_total"] = int((time.monotonic() - inicio) * 1000)
    alguno_ok = any(w.ok for w in resueltos)
    if receta is None and not desde_cache:
        # Lo que el modelo resolvio bien (sin error, sin reparacion, con filas) se guarda
        # para servir de ejemplo a la siguiente pregunta parecida.
        for w in resueltos:
            if w.ok and not w.reparada and w.total_filas > 0 and w.sql:
                banco_ej.aprender(pregunta, w.sql, [r.split('.')[-1].lower() for r in security.relaciones_referenciadas(w.sql)], w.total_filas)

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
