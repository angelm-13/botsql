from __future__ import annotations

from tests.conftest import BackendTestCase
from app.services.bank_account_service import BankAccountService


class TestBankAccountService(BackendTestCase):
    def test_crud_service_bank_account(self):
        created = BankAccountService.create({'bank_account_description': 'test description', 'branch': 'test branch', 'type': 'test type', 'ordinary_interest': 10.5, 'moratorium_interest': 10.5, 'anuality': 10.5, 'reimbursement': 10.5, 'created_by': 1})
        self.assertIsNotNone(created)
        page = BankAccountService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)
