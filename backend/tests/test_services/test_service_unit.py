from __future__ import annotations

from tests.conftest import BackendTestCase
from tests.model_factory import build_payload
from app.services.unit_service import UnitService


class TestUnitService(BackendTestCase):
    def test_crud_service_unit(self):
        created = UnitService.create(build_payload(UnitService, {'unit_code': 'test description', 'unit_name': 'test description', 'unit_category': 'test description', 'is_active': True, 'symbol': 'test description', 'measurement_system': 'metric', 'created_by': 1}))
        self.assertIsNotNone(created)
        page = UnitService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)
