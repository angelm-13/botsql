from __future__ import annotations

from datetime import datetime
from tests.conftest import BackendTestCase
from tests.model_factory import build_model
from app.models.session import transaction_context
from app.models.payroll_period import PayrollPeriod


class TestPayrollPeriodModel(BackendTestCase):
    def test_create_serialize_summary_delete_payroll_period(self):
        with transaction_context() as session:
            item = build_model(PayrollPeriod,
            period_start='2026-01-15T12:00:00',
            period_end='2026-01-15T12:00:00',
            payment_date='2026-01-15T12:00:00',
            created_by=1
            )
            session.add(item)
            session.flush()
            data = item.serialize()
            self.assertIsInstance(data, dict)
            summary = item.serialize_summary()
            self.assertIsInstance(summary, dict)
            session.delete(item)
