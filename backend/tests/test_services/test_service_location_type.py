from __future__ import annotations

from tests.conftest import BackendTestCase
from app.services.location_type_service import LocationTypeService


class TestLocationTypeService(BackendTestCase):
    def test_crud_service_location_type(self):
        created = LocationTypeService.create({'location_type_description': 'test description', 'created_by': 1})
        self.assertIsNotNone(created)
        page = LocationTypeService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)
