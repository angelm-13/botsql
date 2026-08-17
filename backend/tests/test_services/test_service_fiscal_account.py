from __future__ import annotations

from tests.conftest import BackendTestCase
from tests.model_factory import build_payload
from app.services.fiscal_account_service import FiscalAccountService


class TestFiscalAccountService(BackendTestCase):
    def test_crud_service_fiscal_account(self):
        created = FiscalAccountService.create(build_payload(FiscalAccountService, {'fiscal_account_description': 'test description', 'balance': 10.5, 'created_by': 1}))
        self.assertIsNotNone(created)
        page = FiscalAccountService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)
