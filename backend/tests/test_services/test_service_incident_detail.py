from __future__ import annotations

from tests.conftest import BackendTestCase
from tests.model_factory import build_payload
from app.services.incident_detail_service import IncidentDetailService


class TestIncidentDetailService(BackendTestCase):
    def test_crud_service_incident_detail(self):
        created = IncidentDetailService.create(build_payload(IncidentDetailService, {'incident_detail_name': 'test description', 'incident_detail_description': 'test description', 'created_by': 1}))
        self.assertIsNotNone(created)
        page = IncidentDetailService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)
