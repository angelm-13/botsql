from __future__ import annotations

from tests.conftest import BackendTestCase
from tests.model_factory import build_payload
from app.services.payroll_period_service import PayrollPeriodService


class TestPayrollPeriodService(BackendTestCase):
    def test_crud_service_payroll_period(self):
        created = PayrollPeriodService.create(build_payload(PayrollPeriodService, {'period_start': '2026-01-15T12:00:00', 'period_end': '2026-01-15T12:00:00', 'payment_date': '2026-01-15T12:00:00', 'created_by': 1}))
        self.assertIsNotNone(created)
        page = PayrollPeriodService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)
