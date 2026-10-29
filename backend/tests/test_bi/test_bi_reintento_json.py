"""Si el modelo contesta una pregunta simple con un tablero cortado a medio JSON, se reintenta una vez."""

import json
from types import SimpleNamespace

from sqlalchemy import create_engine, text

from app.bi import service
from app.bi.config import AjustesBI
from app.bi.llm_provider import ProveedorLLM
from app.bi.schema_extractor import CacheDeEsquema

CORTADO = '{"is_dashboard": true, "dashboard_title": "x", "widgets": [{"sql_query": "SELECT 1 FROM product", "visualization": {"chart_type": "bar"'
BUENO = json.dumps({"is_dashboard": False, "sql_query": "SELECT descripcion AS d, COUNT(*) AS n FROM product GROUP BY 1",
                    "explanation": "x", "visualization": {"chart_type": "table", "title": "t"}})


class Falso(ProveedorLLM):
    def __init__(self, respuestas):
        self.respuestas, self.llamadas = list(respuestas), []

    def generar(self, prompt, pregunta="", formato=None):
        self.llamadas.append(prompt)
        return SimpleNamespace(texto=self.respuestas.pop(0), modelo="falso", ms=1, tokens_prompt=1, tokens_respuesta=1)

    def disponible(self):
        return True


def _responder(proveedor, pregunta):
    e = create_engine("sqlite://")
    with e.begin() as c:
        c.execute(text("CREATE TABLE product (id_product INTEGER PRIMARY KEY, descripcion TEXT, deletion_date TEXT)"))
        c.execute(text("INSERT INTO product (descripcion) VALUES ('martillo')"))
    aj = AjustesBI()
    return service.responder(pregunta, engine=e, proveedor=proveedor, ajustes=aj, cache_esquema=CacheDeEsquema(e, aj))


def test_json_cortado_se_reintenta_una_vez_y_responde():
    p = Falso([CORTADO, BUENO])
    r = _responder(p, "que descripcion tienen los registros agrupados")
    assert r.ok and len(p.llamadas) == 2 and "UN solo objeto JSON" in p.llamadas[1] and r.meta.get("reintento")


def test_si_el_reintento_tambien_falla_se_reporta_el_error():
    r = _responder(Falso([CORTADO, CORTADO]), "que descripcion tienen los registros agrupados")
    assert not r.ok and r.http == 502 and r.error["tipo"] == "directiva_invalida"


def test_una_pregunta_de_tablero_no_se_reintenta():
    p = Falso([CORTADO])
    r = _responder(p, "dame un dashboard de productos")
    assert not r.ok and len(p.llamadas) == 1
