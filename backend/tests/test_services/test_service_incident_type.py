from __future__ import annotations

from tests.conftest import BackendTestCase
from app.services.incident_type_service import IncidentTypeService


class TestIncidentTypeService(BackendTestCase):
    def test_crud_service_incident_type(self):
        created = IncidentTypeService.create({'incident_type_description': 'test description', 'created_by': 1})
        self.assertIsNotNone(created)
        page = IncidentTypeService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)
