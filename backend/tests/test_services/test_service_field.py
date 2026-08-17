from __future__ import annotations

from tests.conftest import BackendTestCase
from tests.model_factory import build_payload
from app.services.field_service import FieldService


class TestFieldService(BackendTestCase):
    def test_crud_service_field(self):
        created = FieldService.create(build_payload(FieldService, {'created_by': 1, 'table_name': 'user', 'field_name': 'id_user'}))
        self.assertIsNotNone(created)
        page = FieldService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)
