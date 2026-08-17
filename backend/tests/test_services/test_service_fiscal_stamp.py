from __future__ import annotations

from tests.conftest import BackendTestCase
from app.services.fiscal_stamp_service import FiscalStampService


class TestFiscalStampService(BackendTestCase):
    def test_crud_service_fiscal_stamp(self):
        created = FiscalStampService.create({'concept': 'test concept', 'reviewed_by': 1, 'authorized_by': 1, 'auxiliar': 'test auxiliar', 'num_policy': 'test num_policy', 'created_by': 1})
        self.assertIsNotNone(created)
        page = FiscalStampService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)
