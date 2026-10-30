"""Lo que acorta el tiempo de una pregunta: formato compacto, prefijo estable y tablero precocinado."""

import json
from datetime import date
from types import SimpleNamespace

from sqlalchemy import create_engine, text

from app.bi import directive, prompt as prompt_mod, recetas, service
from app.bi.config import AjustesBI
from app.bi.llm_provider import ESQUEMA_CONSULTA, ProveedorLLM
from app.bi.schema_extractor import CacheDeEsquema


class Espia(ProveedorLLM):
    def __init__(self, respuesta):
        self.respuesta, self.llamadas = respuesta, []

    def generar(self, prompt, pregunta="", formato=None):
        self.llamadas.append({"prompt": prompt, "formato": formato})
        return SimpleNamespace(texto=self.respuesta, modelo="falso", ms=1, tokens_prompt=1, tokens_respuesta=1)

    def disponible(self):
        return True


def _entorno():
    e = create_engine("sqlite://")
    with e.begin() as c:
        c.execute(text("CREATE TABLE product (id_product INTEGER PRIMARY KEY, descripcion TEXT, cantidad INTEGER, deletion_date TEXT)"))
        c.execute(text("INSERT INTO product (descripcion, cantidad) VALUES ('martillo', 3), ('taladro', 9)"))
    aj = AjustesBI()
    return e, aj, CacheDeEsquema(e, aj)


def _responder(proveedor, pregunta):
    e, aj, cache = _entorno()
    return service.responder(pregunta, engine=e, proveedor=proveedor, ajustes=aj, cache_esquema=cache)


SOLO_SQL = json.dumps({"sql_query": "SELECT descripcion AS producto, cantidad AS existencias FROM product ORDER BY cantidad DESC"})


def test_una_pregunta_simple_pide_solo_el_sql_al_modelo():
    p = Espia(SOLO_SQL)
    r = _responder(p, "que productos hay ordenados por existencias")
    assert r.ok and len(p.llamadas) == 1
    llamada = p.llamadas[0]
    assert llamada["formato"] == ESQUEMA_CONSULTA
    assert '{"sql_query": "SELECT ..."}' in llamada["prompt"]
    # el contrato completo (visualizacion, tableros) ya no viaja en el prompt
    assert '"visualization"' not in llamada["prompt"] and '"widgets"' not in llamada["prompt"]


def test_sin_titulo_del_modelo_la_pregunta_hace_de_titulo():
    r = _responder(Espia(SOLO_SQL), "¿que productos hay ordenados por existencias?")
    w = r.widgets[0]
    assert w.ok and w.visualization["title"] == "Que productos hay ordenados por existencias"
    assert w.total_filas == 2


def test_una_pregunta_de_tablero_conserva_el_contrato_completo():
    contrato = json.dumps({"is_dashboard": True, "dashboard_title": "t", "widgets": [
        {"sql_query": "SELECT COUNT(*) AS n FROM product", "visualization": {"chart_type": "kpi_card", "title": "Total", "y_axis": "n"}}]})
    p = Espia(contrato)
    r = _responder(p, "dame un dashboard de productos")
    assert r.ok and p.llamadas[0]["formato"] is None
    assert '"widgets"' in p.llamadas[0]["prompt"]


def test_orden_del_prompt_fijo_primero_pregunta_al_final():
    e, aj, cache = _entorno()
    esquema = cache.obtener()
    t = prompt_mod.construir_prompt("cuantos productos hay", esquema, limite_filas=1000, hoy=date(2026, 10, 30),
                                    ejemplos="EJEMPLOS REALES x\n\n", compacto=True)
    assert t.index("GLOSARIO") < t.index("### MOTOR") < t.index("### ESQUEMA") < t.index("EJEMPLOS REALES") < t.index("### PREGUNTA")
    assert t.rstrip().endswith("cuantos productos hay")


def test_el_prefijo_estable_abre_el_prompt_de_cualquier_pregunta_y_formato():
    e, aj, cache = _entorno()
    esquema = cache.obtener()
    hoy = date(2026, 10, 30)
    prefijo = prompt_mod.prefijo_estable(esquema, limite_filas=1000, hoy=hoy)
    assert "{" not in prefijo.replace('{"error"', "")  # sin marcadores sin resolver
    for pregunta, compacto in (("cuantos productos hay", True), ("dashboard de productos", False)):
        t = prompt_mod.construir_prompt(pregunta, esquema, limite_filas=1000, hoy=hoy, compacto=compacto)
        assert t.startswith(prefijo), f"el prefijo dejo de ser comun ({'compacto' if compacto else 'completo'})"


def test_el_tablero_general_es_una_receta_que_no_gasta_modelo():
    for frase in ("Dashboard general de operaciones", "resumen de operaciones", "panorama general", "dashboard de operaciones"):
        crudo = recetas.buscar(frase)
        assert crudo is not None, frase
        d = directive.parsear_directiva(crudo)
        assert d.is_dashboard and len(d.widgets) == 6
        assert {w.visualization.chart_type for w in d.widgets} == {"kpi_card", "bar", "line"}
    assert recetas.buscar("dashboard de productos") is None  # ese si lo piensa el modelo


def test_el_tablero_general_no_llama_al_modelo():
    p = Espia("no debia usarse")
    _responder(p, "Dashboard general de operaciones")
    assert p.llamadas == []


def test_titulo_de_la_pregunta():
    assert service._titulo_de("  ¿Cuántos   productos hay?  ") == "Cuántos productos hay"
    assert service._titulo_de("") == "Resultados"
    assert len(service._titulo_de("x" * 200)) <= 90
