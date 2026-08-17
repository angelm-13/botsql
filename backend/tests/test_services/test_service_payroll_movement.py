from __future__ import annotations

from tests.conftest import BackendTestCase
from tests.model_factory import build_payload
from app.services.payroll_movement_service import PayrollMovementService


class TestPayrollMovementService(BackendTestCase):
    def test_crud_service_payroll_movement(self):
        created = PayrollMovementService.create(build_payload(PayrollMovementService, {'amount': 10.5, 'created_by': 1}))
        self.assertIsNotNone(created)
        page = PayrollMovementService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)
