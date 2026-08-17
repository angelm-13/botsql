from __future__ import annotations

from datetime import datetime
from tests.conftest import BackendTestCase
from app.models.nm_incident_product import NmIncidentProduct


class TestNmIncidentProductModel(BackendTestCase):
    def test_create_serialize_summary_delete_nm_incident_product(self):
        with transaction_context() as session:
            item = NmIncidentProduct(
            note='test note',
            quantity=1,
            close_date='datetime.now()',
            created_by=1
            )
            session.add(item)
            session.flush()
            data = item.serialize()
            self.assertIsInstance(data, dict)
            summary = item.serialize_summary()
            self.assertIsInstance(summary, dict)
            session.delete(item)
