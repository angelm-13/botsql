from __future__ import annotations

from tests.conftest import BackendTestCase
from app.services.location_service import LocationService


class TestLocationService(BackendTestCase):
    def test_crud_service_location(self):
        created = LocationService.create({'location_description': 'test description', 'created_by': 1})
        self.assertIsNotNone(created)
        page = LocationService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)
