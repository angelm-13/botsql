from __future__ import annotations

from tests.conftest import BackendTestCase
from app.services.payroll_period_service import PayrollPeriodService


class TestPayrollPeriodService(BackendTestCase):
    def test_crud_service_payroll_period(self):
        created = PayrollPeriodService.create({'period_start': 'datetime.now()', 'period_end': 'datetime.now()', 'payment_date': 'datetime.now()', 'created_by': 1})
        self.assertIsNotNone(created)
        page = PayrollPeriodService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)
