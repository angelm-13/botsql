from __future__ import annotations

from tests.conftest import BackendTestCase
from app.services.incident_service import IncidentService


class TestIncidentService(BackendTestCase):
    def test_crud_service_incident(self):
        created = IncidentService.create({'incident_date': 'datetime.now()', 'note': 'test note', 'incident_status': 'test state', 'close_date': 'datetime.now()', 'created_by': 1})
        self.assertIsNotNone(created)
        page = IncidentService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)
