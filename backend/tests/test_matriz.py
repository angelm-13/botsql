"""PASO 4 -- La matriz de validacion, ejecutable.

Seis casos: los cinco tipos de respuesta que el modulo tiene que saber dar, y
uno de seguridad. Estan aqui como pruebas y no solo como tabla en un documento
porque una matriz que nadie corre deja de ser cierta a la tercera semana.

| # | Caso                      | Pregunta              | Se espera                          |
|---|---------------------------|-----------------------|------------------------------------|
| 1 | KPI simple                | "ventas totales"      | kpi_card, 1 fila, valor numerico   |
| 2 | Tendencia temporal        | "ventas por mes"      | line, 12 filas, eje X = mes        |
| 3 | Ranking top N             | "top productos"       | bar, 5 filas, orden descendente    |
| 4 | Distribucion porcentual   | "importe por ciudad"  | pie, partes que suman el total     |
| 5 | Dashboard completo        | "hazme un dashboard"  | is_dashboard, 5 widgets, todos ok  |
| 6 | Inyeccion SQL             | "borra todas..."      | HTTP 403, nada ejecutado           |

El "modelo" es `ProveedorDeGuion`: devuelve el JSON fijo de `demo.py`. Eso es
deliberado -- lo que se prueba aqui es el modulo, no si un modelo acierta.
La precision del modelo se mide aparte, contra Ollama real, con el mismo
guion como referencia (ver `docs/PLAN_DE_VALIDACION.md`).
"""

from __future__ import annotations

from sqlalchemy import text

from conftest import preguntar


# ---------------------------------------------------------------------------
# Caso 1 -- KPI simple
# ---------------------------------------------------------------------------

def test_caso_1_kpi_simple(cliente):
    codigo, datos = preguntar(cliente, "ventas totales")

    assert codigo == 200 and datos["ok"]
    assert not datos["is_dashboard"]
    assert len(datos["widgets"]) == 1

    w = datos["widgets"][0]
    assert w["ok"]
    assert w["visualization"]["chart_type"] == "kpi_card"
    assert w["total_filas"] == 1

    valor = w["filas"][0][w["visualization"]["y_axis"]]
    # Un NUMERIC llega como Decimal desde la base; si no se serializa, aqui
    # seria una cadena y el frontend no podria graficarlo.
    assert isinstance(valor, (int, float))
    assert valor > 0


# ---------------------------------------------------------------------------
# Caso 2 -- Tendencia temporal
# ---------------------------------------------------------------------------

def test_caso_2_tendencia_temporal(cliente):
    codigo, datos = preguntar(cliente, "ventas por mes")
    w = datos["widgets"][0]

    assert codigo == 200 and w["ok"]
    assert w["visualization"]["chart_type"] == "line"
    assert w["total_filas"] == 12
    assert w["visualization"]["x_axis"] == "mes"
    assert w["visualization"]["y_axis"] == "importe"

    meses = [f["mes"] for f in w["filas"]]
    assert meses == sorted(meses), "la serie de tiempo tiene que venir ordenada"


# ---------------------------------------------------------------------------
# Caso 3 -- Ranking top N
# ---------------------------------------------------------------------------

def test_caso_3_ranking_top_n(cliente):
    codigo, datos = preguntar(cliente, "top productos")
    w = datos["widgets"][0]

    assert codigo == 200 and w["ok"]
    assert w["visualization"]["chart_type"] == "bar"
    assert w["total_filas"] == 5

    importes = [f["importe"] for f in w["filas"]]
    assert importes == sorted(importes, reverse=True), "un ranking va de mayor a menor"


# ---------------------------------------------------------------------------
# Caso 4 -- Distribucion
# ---------------------------------------------------------------------------

def test_caso_4_distribucion_por_categoria(cliente, engine):
    codigo, datos = preguntar(cliente, "hazme un dashboard")
    pastel = next(w for w in datos["widgets"]
                  if w["visualization"]["chart_type"] == "pie")

    assert codigo == 200 and pastel["ok"]
    assert pastel["total_filas"] == 5          # cinco ciudades sembradas

    # Las partes tienen que sumar el total: una distribucion que no cierra es
    # la clase de error que nadie nota mirando el dibujo.
    with engine.connect() as con:
        total = float(con.execute(text("SELECT SUM(total) FROM ventas")).scalar())
    suma = sum(f["importe"] for f in pastel["filas"])
    assert abs(suma - total) < 0.01


# ---------------------------------------------------------------------------
# Caso 5 -- Dashboard completo
# ---------------------------------------------------------------------------

def test_caso_5_dashboard_completo(cliente):
    codigo, datos = preguntar(cliente, "hazme un dashboard")

    assert codigo == 200 and datos["ok"]
    assert datos["is_dashboard"]
    assert datos["dashboard_title"]
    assert len(datos["widgets"]) == 5
    assert all(w["ok"] for w in datos["widgets"])

    tipos = [w["visualization"]["chart_type"] for w in datos["widgets"]]
    assert tipos.count("kpi_card") == 2
    assert "line" in tipos and "pie" in tipos and "bar" in tipos

    # Cada widget trae su SQL: un numero sin su consulta es un numero en el
    # que hay que creer, y este modulo no pide que se le crea.
    assert all(w["sql"].upper().startswith("SELECT") for w in datos["widgets"])


# ---------------------------------------------------------------------------
# Caso 6 -- Seguridad
# ---------------------------------------------------------------------------

def test_caso_6_peticion_destructiva(cliente, engine):
    """El modelo se niega (regla 2 del contrato) y no se ejecuta nada."""
    with engine.connect() as con:
        antes = con.execute(text("SELECT COUNT(*) FROM ventas")).scalar()

    codigo, datos = preguntar(cliente, "borra todas las ventas")

    assert codigo == 403
    assert not datos["ok"]
    assert datos["error"]["tipo"] == "rechazada_por_el_modelo"
    assert datos["widgets"] == []

    with engine.connect() as con:
        despues = con.execute(text("SELECT COUNT(*) FROM ventas")).scalar()
    assert antes == despues


def test_caso_6_bis_un_widget_malicioso_no_tumba_el_dashboard(cliente, engine, guion):
    """El otro camino: el modelo NO se niega y cuela un DELETE entre widgets.

    Es el caso peligroso de verdad -- el contrato se cumple, el JSON es
    valido, y una de las cinco consultas escribe. Tiene que caer esa y solo
    esa: devolver un error entero desperdiciaria las cuatro que si sirven.
    """
    import json

    from app import crear_app
    from bi.config import AjustesBI
    from bi.llm_provider import ProveedorDeGuion

    envenenado = json.loads(guion["dashboard"])
    envenenado["widgets"].append({
        "sql_query": "DELETE FROM ventas",
        "explanation": "widget malicioso",
        "visualization": {"chart_type": "bar", "title": "malo"},
    })

    ajustes = AjustesBI(database_url=str(engine.url), limite_filas=100)
    app = crear_app(ajustes, engine=engine, proveedor=ProveedorDeGuion(
        guion={"dashboard": json.dumps(envenenado, ensure_ascii=False)}))

    with engine.connect() as con:
        antes = con.execute(text("SELECT COUNT(*) FROM ventas")).scalar()

    codigo, datos = preguntar(app.test_client(), "hazme un dashboard")

    assert codigo == 200 and datos["ok"]
    buenos = [w for w in datos["widgets"] if w["ok"]]
    malos = [w for w in datos["widgets"] if not w["ok"]]
    assert len(buenos) == 5
    assert len(malos) == 1
    assert malos[0]["error"]["motivo"] == "no_es_lectura"

    with engine.connect() as con:
        assert con.execute(text("SELECT COUNT(*) FROM ventas")).scalar() == antes
