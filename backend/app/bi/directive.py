"""Parser seguro de la directiva que devuelve el modelo.

Un modelo pequeno cumple el contrato casi siempre. "Casi" es el problema: si
el parser confia, un dia el servidor devuelve 500 en vez de una respuesta
util. Aqui se asume que la salida puede venir sucia y se normaliza:

  * envuelta en ```json ... ``` aunque se pidio que no;
  * con prosa antes o despues del objeto;
  * con `chart_type` inventado ("barchart", "grafica_de_barras");
  * con `widgets` siendo un objeto en vez de una lista;
  * con `sql_query` como lista de lineas;
  * con un dashboard de 40 widgets porque el modelo se entusiasmo.

Lo que NO se normaliza es el SQL. Si viene raro, lo rechaza `security.py`.
Este archivo solo se ocupa de la forma del JSON.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field

# Los unicos tipos que el frontend sabe dibujar. Cualquier otra cosa degrada
# a tabla: una tabla siempre puede mostrar el resultado, asi que un tipo
# desconocido nunca deja al usuario sin respuesta.
TIPOS_DE_GRAFICA = ("bar", "line", "pie", "area", "kpi_card", "table")

# Como escriben los modelos lo que quieren decir.
SINONIMOS_DE_TIPO: dict[str, str] = {
    "barchart": "bar", "bar_chart": "bar", "barras": "bar", "column": "bar",
    "columnas": "bar", "histogram": "bar", "vertical_bar": "bar",
    "linechart": "line", "line_chart": "line", "linea": "line",
    "lineas": "line", "trend": "line", "timeseries": "line", "time_series": "line",
    "piechart": "pie", "pie_chart": "pie", "pastel": "pie", "donut": "pie",
    "doughnut": "pie", "distribucion": "pie",
    "kpi": "kpi_card", "kpicard": "kpi_card", "card": "kpi_card",
    "metric": "kpi_card", "tarjeta": "kpi_card", "scorecard": "kpi_card",
    "number": "kpi_card", "single_value": "kpi_card",
    "tabla": "table", "grid": "table", "datatable": "table", "list": "table",
    "areachart": "area", "area_chart": "area",
}


class DirectivaInvalida(Exception):
    """La respuesta del modelo no tiene la forma del contrato."""

    def __init__(self, motivo: str, crudo: str = ""):
        self.motivo = motivo
        self.crudo = crudo[:2000]
        super().__init__(motivo)


@dataclass
class Visualizacion:
    chart_type: str = "table"
    title: str = ""
    x_axis: str = ""
    y_axis: str = ""
    metric_label: str = ""
    recommended: bool = True

    def a_dict(self) -> dict:
        return {
            "chart_type": self.chart_type,
            "title": self.title,
            "x_axis": self.x_axis,
            "y_axis": self.y_axis,
            "metric_label": self.metric_label,
            "recommended": self.recommended,
        }


@dataclass
class Widget:
    sql_query: str
    explanation: str = ""
    visualization: Visualizacion = field(default_factory=Visualizacion)


@dataclass
class Directiva:
    is_dashboard: bool
    widgets: list[Widget]
    dashboard_title: str = ""
    error: str = ""          # el modelo se nego, segun la regla 2 del contrato

    @property
    def rechazada_por_el_modelo(self) -> bool:
        return bool(self.error)


# ---------------------------------------------------------------------------
# Extraccion del JSON
# ---------------------------------------------------------------------------

_VALLA = re.compile(r"```(?:json|JSON)?\s*(.*?)```", re.DOTALL)


def extraer_json(texto: str) -> dict:
    """Saca el objeto JSON de la respuesta, venga como venga.

    El recorte por llaves balanceadas es lo que salva el caso mas comun de
    todos: el modelo explica en prosa lo que va a hacer y luego suelta el
    objeto. Buscar de la primera `{` a la ultima `}` fallaria si hay una
    llave dentro de un literal SQL, asi que se cuentan llaves respetando
    comillas y escapes.
    """
    if not texto or not texto.strip():
        raise DirectivaInvalida("respuesta_vacia", texto)

    candidato = texto.strip()

    valla = _VALLA.search(candidato)
    if valla:
        candidato = valla.group(1).strip()

    try:
        datos = json.loads(candidato)
    except ValueError:
        recorte = _recortar_objeto(candidato)
        if recorte is None:
            raise DirectivaInvalida("no_es_json", texto) from None
        try:
            datos = json.loads(recorte)
        except ValueError:
            raise DirectivaInvalida("json_mal_formado", texto) from None

    if not isinstance(datos, dict):
        raise DirectivaInvalida("json_no_es_objeto", texto)
    return datos


def _recortar_objeto(texto: str) -> str | None:
    inicio = texto.find("{")
    if inicio == -1:
        return None

    profundidad = 0
    en_cadena = False
    escapando = False
    for i in range(inicio, len(texto)):
        c = texto[i]
        if escapando:
            escapando = False
            continue
        if c == "\\":
            escapando = True
            continue
        if c == '"':
            en_cadena = not en_cadena
            continue
        if en_cadena:
            continue
        if c == "{":
            profundidad += 1
        elif c == "}":
            profundidad -= 1
            if profundidad == 0:
                return texto[inicio:i + 1]
    return None


# ---------------------------------------------------------------------------
# Normalizacion
# ---------------------------------------------------------------------------

def _texto(valor, omision: str = "") -> str:
    """Una cadena, aunque el modelo haya mandado una lista o un numero."""
    if valor is None:
        return omision
    if isinstance(valor, str):
        return valor.strip()
    if isinstance(valor, (list, tuple)):
        return " ".join(_texto(v) for v in valor).strip()
    return str(valor).strip()


# Palabras que delatan la intencion cuando el nombre exacto no coincide. El
# orden importa: se prueba de la mas especifica a la mas generica, porque
# "grafica_de_barras" contiene "bar" y "tabla" contiene "tab".
_PALABRAS_DE_TIPO: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("kpi_card", ("kpi", "tarjeta", "indicador", "scorecard", "metric", "single")),
    ("pie", ("pie", "pastel", "dona", "donut", "circular", "porcentaje", "reparto")),
    ("line", ("line", "linea", "tendencia", "temporal", "serie", "evolucion")),
    ("area", ("area",)),
    ("bar", ("bar", "barra", "column", "columna", "histogram", "ranking", "top")),
    ("table", ("table", "tabla", "grid", "lista", "detalle")),
)


def _sin_acentos(texto: str) -> str:
    """Quita los acentos antes de comparar.

    Sin esto, "grafico de lineas" se reconoce y "gráfico de líneas" no -- y el
    modelo contesta en el idioma de la pregunta, con sus acentos puestos. El
    sintoma es silencioso: la grafica degrada a tabla y nadie sabe por que.
    """
    return "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )


def normalizar_tipo(bruto) -> str:
    """Del texto del modelo a uno de los tipos que el frontend sabe dibujar.

    El barrido por palabra clave existe porque el modelo contesta en el
    idioma de la pregunta: pide `"grafica_de_barras"` o `"grafico de lineas"`
    aunque el contrato enumere los valores en ingles. Sin esto degradaba todo
    a tabla, que "funciona" pero convierte el modulo en un visor de filas.
    """
    t = _sin_acentos(_texto(bruto).lower()).replace("-", "_").replace(" ", "_")
    if not t:
        return "table"
    if t in TIPOS_DE_GRAFICA:
        return t
    if t in SINONIMOS_DE_TIPO:
        return SINONIMOS_DE_TIPO[t]
    for tipo, palabras in _PALABRAS_DE_TIPO:
        if any(p in t for p in palabras):
            return tipo
    return "table"


def _visualizacion(bruto) -> Visualizacion:
    if not isinstance(bruto, dict):
        return Visualizacion()
    return Visualizacion(
        chart_type=normalizar_tipo(bruto.get("chart_type")),
        title=_texto(bruto.get("title")),
        x_axis=_texto(bruto.get("x_axis")),
        y_axis=_texto(bruto.get("y_axis")),
        metric_label=_texto(bruto.get("metric_label")),
        recommended=bool(bruto.get("recommended", True)),
    )


def _widget(bruto) -> Widget | None:
    if not isinstance(bruto, dict):
        return None
    sql = _texto(bruto.get("sql_query") or bruto.get("sql") or bruto.get("query"))
    if not sql:
        return None
    return Widget(
        sql_query=sql,
        explanation=_texto(bruto.get("explanation") or bruto.get("explicacion")),
        visualization=_visualizacion(bruto.get("visualization") or bruto.get("visualizacion")),
    )


def parsear_directiva(texto: str, *, max_widgets: int = 8) -> Directiva:
    """Del texto crudo del modelo a una directiva con forma garantizada."""
    datos = extraer_json(texto)

    # Regla 2 del contrato: el modelo se nego.
    error = _texto(datos.get("error"))
    if error:
        return Directiva(is_dashboard=False, widgets=[], error=error)

    es_dashboard = bool(datos.get("is_dashboard"))
    brutos = datos.get("widgets")

    # Un modelo puede mandar `is_dashboard: true` sin widgets, o widgets sin
    # la bandera. Manda la evidencia -- que haya widgets -- y no la bandera.
    if isinstance(brutos, dict):
        brutos = list(brutos.values())
    if isinstance(brutos, list) and brutos:
        widgets = [w for w in (_widget(b) for b in brutos) if w is not None]
        if not widgets:
            raise DirectivaInvalida("dashboard_sin_consultas", texto)
        return Directiva(
            is_dashboard=True,
            widgets=widgets[:max_widgets],
            dashboard_title=_texto(datos.get("dashboard_title") or datos.get("title"))
            or "Dashboard",
        )

    unico = _widget(datos)
    if unico is None:
        raise DirectivaInvalida("sin_consulta", texto)

    if es_dashboard:
        # Dijo dashboard y mando una sola consulta: se respeta el dato, no la
        # etiqueta. Un "dashboard" de un widget es una grafica.
        return Directiva(
            is_dashboard=False,
            widgets=[unico],
            dashboard_title=_texto(datos.get("dashboard_title")),
        )

    return Directiva(is_dashboard=False, widgets=[unico])
