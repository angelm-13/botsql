from __future__ import annotations

from tests.conftest import BackendTestCase
from app.services.material_service import MaterialService


class TestMaterialService(BackendTestCase):
    def test_crud_service_material(self):
        created = MaterialService.create({'material_description': 'test description', 'created_by': 1})
        self.assertIsNotNone(created)
        page = MaterialService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)
