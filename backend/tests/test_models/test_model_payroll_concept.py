from __future__ import annotations

from datetime import datetime
from tests.conftest import BackendTestCase
from app.models.payroll_concept import PayrollConcept


class TestPayrollConceptModel(BackendTestCase):
    def test_create_serialize_summary_delete_payroll_concept(self):
        with transaction_context() as session:
            item = PayrollConcept(
            payroll_code='test title',
            payroll_concept_description='test title',
            type='earning',
            is_taxable=True,
            is_imss=True,
            created_by=1
            )
            session.add(item)
            session.flush()
            data = item.serialize()
            self.assertIsInstance(data, dict)
            summary = item.serialize_summary()
            self.assertIsInstance(summary, dict)
            session.delete(item)
