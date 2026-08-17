from __future__ import annotations

from datetime import datetime
from tests.conftest import BackendTestCase
from app.models.incident import Incident


class TestIncidentModel(BackendTestCase):
    def test_create_serialize_summary_delete_incident(self):
        with transaction_context() as session:
            item = Incident(
            incident_date='datetime.now()',
            note='test note',
            incident_status='test state',
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
