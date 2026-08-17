from __future__ import annotations

from datetime import datetime
from tests.conftest import BackendTestCase
from app.models.payroll_period import PayrollPeriod


class TestPayrollPeriodModel(BackendTestCase):
    def test_create_serialize_summary_delete_payroll_period(self):
        with transaction_context() as session:
            item = PayrollPeriod(
            period_start='datetime.now()',
            period_end='datetime.now()',
            payment_date='datetime.now()',
            created_by=1
            )
            session.add(item)
            session.flush()
            data = item.serialize()
            self.assertIsInstance(data, dict)
            summary = item.serialize_summary()
            self.assertIsInstance(summary, dict)
            session.delete(item)
