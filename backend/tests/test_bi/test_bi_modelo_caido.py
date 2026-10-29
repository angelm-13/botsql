"""RNF-09: si el modelo no esta disponible, la API contesta 503 con un mensaje claro y las
respuestas que no necesitan modelo (recetas) siguen funcionando."""

from sqlalchemy import create_engine, text

from app.bi import service
from app.bi.config import AjustesBI
from app.bi.llm_provider import ProveedorLLM, ProveedorNoDisponible
from app.bi.schema_extractor import CacheDeEsquema


class ModeloCaido(ProveedorLLM):
    def generar(self, prompt, pregunta="", formato=None):
        raise ProveedorNoDisponible("sin conexion")

    def disponible(self):
        return False


def _motor():
    e = create_engine("sqlite://")
    with e.begin() as c:
        c.execute(text("CREATE TABLE product (id_product INTEGER PRIMARY KEY, descripcion TEXT, deletion_date TEXT)"))
        c.execute(text("INSERT INTO product (descripcion) VALUES ('martillo'), ('taladro')"))
    return e


def _responder(pregunta):
    e, aj = _motor(), AjustesBI()
    return service.responder(pregunta, engine=e, proveedor=ModeloCaido(), ajustes=aj,
                             cache_esquema=CacheDeEsquema(e, aj))


def test_sin_modelo_una_pregunta_libre_da_503_con_mensaje():
    r = _responder("que producto se vende mas los martes por la tarde")
    assert r.http == 503 and not r.ok and r.error["mensaje"]


def test_sin_modelo_una_receta_sigue_funcionando():
    r = _responder("cuantos productos hay")
    assert r.ok and r.widgets[0].filas[0]["total_productos"] == 2
