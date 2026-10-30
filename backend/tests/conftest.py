from __future__ import annotations

import os
import sys
import unittest
import warnings
from pathlib import Path
from datetime import datetime
from sqlalchemy.exc import SAWarning

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("TESTING", "1")
# Las pruebas son un entorno que NO es produccion (is_production falla cerrado).
os.environ.setdefault("APP_ENV", "testing")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("JWT_SS", "test-secret")
os.environ.setdefault("MFA_ISSUER", "TYAKXA Test")

try:
    from app import create_app
    from app.models.base import Base
    from app.models.session import engine, transaction_context
except Exception as exc:  # pragma: no cover
    create_app = None
    Base = None
    engine = None
    transaction_context = None
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None


def reset_test_database():
    """Deja la base limpia entre pruebas.

    Con SQLite en memoria basta cerrar el pool: la base se va con el.

    Con PostgreSQL se tira el esquema entero en lugar de ir tabla por tabla.
    `drop_all` tiene que ordenar los DROP y no puede: hay un ciclo real de
    llaves foraneas entre `permission`, `user`, `proyect` y `customer_supplier`
    -el mismo que obligo a declararlas diferibles para poder sembrar-, asi que
    revienta con CircularDependencyError. `DROP SCHEMA ... CASCADE` no necesita
    orden y ademas se lleva por delante secuencias e indices.
    """
    if engine.dialect.name == 'sqlite':
        engine.dispose()
    else:
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', SAWarning)
            with engine.begin() as conexion:
                conexion.exec_driver_sql('DROP SCHEMA public CASCADE')
                conexion.exec_driver_sql('CREATE SCHEMA public')
    Base.metadata.create_all(bind=engine)


class BackendTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if IMPORT_ERROR:
            raise IMPORT_ERROR
        cls.app = create_app(testing=True) if create_app else None
        cls.client = cls.app.test_client() if cls.app else None
        Base.metadata.create_all(bind=engine)

    def setUp(self):
        reset_test_database()

    def tearDown(self):
        reset_test_database()

    def json(self, response):
        return response.get_json() or {}

    def auth_headers(self):
        token = "test-token"
        return {"Authorization": f"Bearer {token}"}
