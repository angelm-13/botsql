"""Analisis predictivo: pronostico estadistico sobre series mensuales reales.

No lo hace el modelo de lenguaje (un 3B inventaria cifras): el SQL de la serie
historica sale de un catalogo verificado, pasa por el mismo validador y el mismo
filtro por rol que cualquier consulta, y el pronostico lo calcula este modulo
con una regresion lineal sobre los meses completos disponibles:

  * valor esperado de cada mes futuro (tendencia lineal, minimos cuadrados),
  * banda de prediccion al ~80 % (+/-1.28 desviaciones del ajuste),
  * R^2 y numero de meses: se dicen siempre, para que se sepa que tanto fiarse.

Con menos de 3 meses no se pronostica; con menos de 6 se avisa que es poco
confiable. Es una proyeccion de tendencia, no una promesa: no ve estacionalidad
ni eventos futuros.
"""

from __future__ import annotations

import math
import re
import unicodedata
from datetime import date, datetime

_HIST = ("date_trunc('month', {col})::date AS mes, {agg} AS valor FROM {tabla} WHERE deletion_date IS NULL "
         "AND {col} >= (date_trunc('month', now()) - interval '24 months') "
         "AND {col} < date_trunc('month', now()) GROUP BY 1 ORDER BY 1")

# (palabras clave, titulo, unidad, SQL de la serie mensual)
SERIES = (
    (r"herramienta|prestamo", "Herramientas prestadas por mes", "piezas",
     "SELECT " + _HIST.format(col="start_date", agg="SUM(quantity)", tabla="nm_incident_product")),
    (r"vale|incidencia", "Vales (incidencias) por mes", "vales",
     "SELECT " + _HIST.format(col="incident_date", agg="COUNT(*)", tabla="incident")),
    (r"punto de venta|\bpos\b|caja|mostrador", "Ventas del punto de venta por mes", "importe",
     "SELECT " + _HIST.format(col="paid_at", agg="SUM(total)", tabla="pos_sale")),
    (r"factur|ingreso|venta", "Facturacion por mes", "importe",
     "SELECT " + _HIST.format(col="date_emision", agg="SUM(total)", tabla="invoice")),
)

_PIDE_PREDICCION = re.compile(
    r"(?i)(predic|pronostic|proyecc|proyecta|prediccion|estimacion futura|tendencia futura|"
    r"a futuro|proximo mes|proximos? " + chr(92) + r"d+ meses|siguiente mes|cuanto (se )?(vendera|facturara|habra|prestara)|"
    r"que tanto (crecera|subira|bajara))")


def _norm(t: str) -> str:
    s = unicodedata.normalize("NFKD", (t or "").lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def es_prediccion(pregunta: str) -> bool:
    return bool(_PIDE_PREDICCION.search(_norm(pregunta)))


def horizonte(pregunta: str) -> int:
    m = re.search(r"(?:proximos?|siguientes?) (" + chr(92) + r"d{1,2}) meses", _norm(pregunta))
    return max(1, min(int(m.group(1)), 12)) if m else 3


def serie_para(pregunta: str):
    """(titulo, unidad, sql) de la serie que corresponde a la pregunta, o None."""
    t = _norm(pregunta)
    for patron, titulo, unidad, sql in SERIES:
        if re.search(patron, t):
            return titulo, unidad, sql
    return None


def _mes(v) -> tuple[int, int] | None:
    if isinstance(v, (date, datetime)):
        return v.year, v.month
    m = re.match(r"(" + chr(92) + r"d{4})-(" + chr(92) + r"d{2})", str(v))
    return (int(m.group(1)), int(m.group(2))) if m else None


def pronosticar(valores: list[float], pasos: int):
    """Regresion lineal simple. Devuelve None si no hay historia suficiente."""
    n = len(valores)
    if n < 3:
        return None
    xs = list(range(n))
    xm = sum(xs) / n
    ym = sum(valores) / n
    sxx = sum((x - xm) ** 2 for x in xs)
    sxy = sum((x - xm) * (y - ym) for x, y in zip(xs, valores))
    b = sxy / sxx if sxx else 0.0
    a = ym - b * xm
    ajuste = [a + b * x for x in xs]
    sse = sum((y - f) ** 2 for y, f in zip(valores, ajuste))
    sst = sum((y - ym) ** 2 for y in valores)
    r2 = 1 - sse / sst if sst else 0.0
    sigma = math.sqrt(sse / (n - 2)) if n > 2 else 0.0
    salida = []
    for h in range(1, pasos + 1):
        x = n - 1 + h
        centro = a + b * x
        ancho = 1.28 * sigma * math.sqrt(1 + 1 / n + ((x - xm) ** 2) / sxx) if sxx else 0.0
        salida.append((max(0.0, centro), max(0.0, centro - ancho), max(0.0, centro + ancho)))
    return {"pasos": salida, "pendiente": b, "r2": r2, "n": n, "promedio": ym}


def construir_tabla(filas: list[dict], pasos: int, unidad: str):
    """(filas de salida, explicacion, avisos) a partir de la serie historica (mes, valor)."""
    hist = []
    for f in filas:
        m = _mes(f.get("mes"))
        v = f.get("valor")
        if m and isinstance(v, (int, float)):
            hist.append((m, float(v)))
    hist.sort()
    if len(hist) < 3:
        return None, "No hay suficiente historia mensual para pronosticar (se necesitan al menos 3 meses completos).", []
    r = pronosticar([v for _, v in hist], pasos)
    salida = [{"mes": f"{y}-{mm:02d}", "valor": round(v, 2), "tipo": "historico", "minimo": None, "maximo": None}
              for (y, mm), v in hist]
    y, mm = hist[-1][0]
    for centro, bajo, alto in r["pasos"]:
        mm += 1
        if mm > 12:
            y, mm = y + 1, 1
        salida.append({"mes": f"{y}-{mm:02d}", "valor": round(centro, 2), "tipo": "pronostico",
                       "minimo": round(bajo, 2), "maximo": round(alto, 2)})
    sentido = "al alza" if r["pendiente"] > 0 else "a la baja" if r["pendiente"] < 0 else "estable"
    explicacion = (f"Proyeccion de los proximos {pasos} meses con tendencia lineal sobre {r['n']} meses completos "
                   f"({unidad}). La tendencia va {sentido}: cambia {r['pendiente']:+.1f} {unidad} por mes. "
                   f"Ajuste R2 = {r['r2']:.2f}. Las columnas minimo y maximo son un rango probable (~80 %).")
    avisos = []
    if r["n"] < 6:
        avisos.append(f"Solo hay {r['n']} meses de historia: el pronostico es poco confiable.")
    if r["r2"] < 0.3:
        avisos.append("La tendencia explica poco de la variacion (R2 bajo): trata el resultado como orientativo.")
    avisos.append("Es una proyeccion de tendencia: no considera estacionalidad ni eventos futuros.")
    return salida, explicacion, avisos
