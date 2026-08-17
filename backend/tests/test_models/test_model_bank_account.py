from __future__ import annotations

from datetime import datetime
from tests.conftest import BackendTestCase
from app.models.bank_account import BankAccount


class TestBankAccountModel(BackendTestCase):
    def test_create_serialize_summary_delete_bank_account(self):
        with transaction_context() as session:
            item = BankAccount(
            bank_account_description='test description',
            branch='test branch',
            type='test type',
            ordinary_interest=10.5,
            moratorium_interest=10.5,
            anuality=10.5,
            reimbursement=10.5,
            created_by=1
            )
            session.add(item)
            session.flush()
            data = item.serialize()
            self.assertIsInstance(data, dict)
            summary = item.serialize_summary()
            self.assertIsInstance(summary, dict)
            session.delete(item)
