"""Piezas compartidas de la suite.

La base de pruebas es la misma de `demo.py`: SQLite sembrada en memoria de
disco temporal. Se eligio SQLite y no PostgreSQL para que la suite corra en
cualquier maquina y en CI sin nada montado -- y donde una prueba dependa de
algo que SQLite no tiene (el reloj por instruccion), se dice en la prueba en
vez de fingir que se probo.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import demo  # noqa: E402
from app import crear_app  # noqa: E402
from bi.config import AjustesBI  # noqa: E402
from bi.llm_provider import ProveedorDeGuion  # noqa: E402
from bi.schema_extractor import CacheDeEsquema, extraer_esquema  # noqa: E402


@pytest.fixture(scope="session")
def ruta_bd(tmp_path_factory) -> Path:
    ruta = tmp_path_factory.mktemp("bi") / "pruebas.db"
    original = demo.RUTA
    demo.RUTA = ruta
    try:
        demo.sembrar()
    finally:
        demo.RUTA = original
    return ruta


@pytest.fixture(scope="session")
def engine(ruta_bd: Path):
    motor = create_engine(f"sqlite:///{ruta_bd}", future=True, poolclass=NullPool)
    yield motor
    motor.dispose()


@pytest.fixture
def ajustes(ruta_bd: Path) -> AjustesBI:
    return AjustesBI(database_url=f"sqlite:///{ruta_bd}", limite_filas=100)


@pytest.fixture
def esquema(engine, ajustes):
    return extraer_esquema(engine, ajustes)


@pytest.fixture
def guion() -> dict[str, str]:
    """El mismo guion de la demo, ya serializado."""
    return {k: json.dumps(v, ensure_ascii=False) for k, v in demo.GUION.items()}


@pytest.fixture
def cliente(engine, ajustes, guion):
    """Un cliente de pruebas de Flask con el modelo simulado."""
    proveedor = ProveedorDeGuion(guion=guion)
    app = crear_app(ajustes, engine=engine, proveedor=proveedor)
    app.extensions["bi"]["cache"] = CacheDeEsquema(engine, ajustes)
    return app.test_client()


def preguntar(cliente, texto: str):
    r = cliente.post("/api/v1/bi/query", json={"prompt": texto})
    return r.status_code, r.get_json()
