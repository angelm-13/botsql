from __future__ import annotations

from tests.conftest import BackendTestCase
from tests.model_factory import build_payload
from app.services.material_component_service import MaterialComponentService


class TestMaterialComponentService(BackendTestCase):
    def test_crud_service_material_component(self):
        created = MaterialComponentService.create(build_payload(MaterialComponentService, {'id_material': 1, 'id_component': 2, 'relation': 10.5, 'created_by': 1}))
        self.assertIsNotNone(created)
        page = MaterialComponentService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)
