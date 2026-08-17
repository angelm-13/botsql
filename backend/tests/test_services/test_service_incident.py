from __future__ import annotations

from tests.conftest import BackendTestCase
from tests.model_factory import build_payload
from app.services.incident_service import IncidentService


class TestIncidentService(BackendTestCase):
    def test_crud_service_incident(self):
        created = IncidentService.create(build_payload(IncidentService, {'incident_date': '2026-01-15T12:00:00', 'note': 'test note', 'incident_status': 'test state', 'close_date': '2026-01-15T12:00:00', 'created_by': 1}))
        self.assertIsNotNone(created)
        page = IncidentService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)
