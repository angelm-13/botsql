from __future__ import annotations

from tests.conftest import BackendTestCase
from app.services.bank_service import BankService


class TestBankService(BackendTestCase):
    def test_crud_service_bank(self):
        created = BankService.create({'bank_name': 'test bank_name', 'created_by': 1})
        self.assertIsNotNone(created)
        page = BankService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)
