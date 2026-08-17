from __future__ import annotations

from tests.conftest import BackendTestCase
from app.services.payroll_detail_service import PayrollDetailService


class TestPayrollDetailService(BackendTestCase):
    def test_crud_service_payroll_detail(self):
        created = PayrollDetailService.create({'gross_salary': 10.5, 'total_earnings': 10.5, 'total_deductions': 10.5, 'net_pay': 10.5, 'created_by': 1})
        self.assertIsNotNone(created)
        page = PayrollDetailService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)
