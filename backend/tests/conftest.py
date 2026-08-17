from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("TESTING", "1")
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


class BackendTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if IMPORT_ERROR:
            raise IMPORT_ERROR
        cls.app = create_app(testing=True) if create_app else None
        cls.client = cls.app.test_client() if cls.app else None
        Base.metadata.create_all(bind=engine)

    def setUp(self):
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)

    def tearDown(self):
        Base.metadata.drop_all(bind=engine)

    def json(self, response):
        return response.get_json() or {}

    def auth_headers(self):
        token = "test-token"
        return {"Authorization": f"Bearer {token}"}
