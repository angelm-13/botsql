"""Un cuerpo mal formado en /query es un 400, nunca un 500 (hallazgo de la prueba de aceptacion)."""

import pytest
from flask import Flask
from sqlalchemy import create_engine

from app.bi.api import crear_blueprint
from app.bi.config import AjustesBI
from app.bi.llm_provider import ProveedorLLM


class SinModelo(ProveedorLLM):
    def generar(self, prompt, pregunta="", formato=None):
        raise AssertionError("una entrada invalida no debe llegar al modelo")

    def disponible(self):
        return True


@pytest.fixture
def cliente():
    app = Flask(__name__)
    ajustes = AjustesBI()
    app.register_blueprint(crear_blueprint(engine=create_engine("sqlite://"), ajustes=ajustes, proveedor=SinModelo()))
    return app.test_client(), ajustes.prefijo_api


@pytest.mark.parametrize("cuerpo", [{"prompt": 12345}, {"prompt": ["a", "b"]}, {"prompt": {"x": 1}},
                                    {"pregunta": 7}, [1, 2, 3], "texto suelto", 42])
def test_un_cuerpo_que_no_es_una_pregunta_en_texto_da_4xx(cliente, cuerpo):
    http, prefijo = cliente
    r = http.post(f"{prefijo}/query", json=cuerpo)
    assert 400 <= r.status_code < 500, r.get_json()
    assert r.get_json()["ok"] is False
