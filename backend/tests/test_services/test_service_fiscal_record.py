from __future__ import annotations

from tests.conftest import BackendTestCase
from app.services.fiscal_record_service import FiscalRecordService


class TestFiscalRecordService(BackendTestCase):
    def test_crud_service_fiscal_record(self):
        created = FiscalRecordService.create({'fiscal_record_name': 'test name', 'amount': 10.5, 'type': 'test type', 'created_by': 1})
        self.assertIsNotNone(created)
        page = FiscalRecordService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)
