from __future__ import annotations

from tests.conftest import BackendTestCase
from tests.model_factory import build_payload
from app.services.level_service import LevelService


class TestLevelService(BackendTestCase):
    def test_crud_service_level(self):
        created = LevelService.create(build_payload(LevelService, {'level_description': 'test description', 'created_by': 1}))
        self.assertIsNotNone(created)
        page = LevelService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)
