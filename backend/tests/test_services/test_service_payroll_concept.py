from __future__ import annotations

from tests.conftest import BackendTestCase
from app.services.payroll_concept_service import PayrollConceptService


class TestPayrollConceptService(BackendTestCase):
    def test_crud_service_payroll_concept(self):
        created = PayrollConceptService.create({'payroll_code': 'test title', 'payroll_concept_description': 'test title', 'type': 'earning', 'is_taxable': True, 'is_imss': True, 'created_by': 1})
        self.assertIsNotNone(created)
        page = PayrollConceptService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)
