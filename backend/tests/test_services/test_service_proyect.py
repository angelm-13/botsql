from __future__ import annotations

from tests.conftest import BackendTestCase
from app.services.proyect_service import ProyectService


class TestProyectService(BackendTestCase):
    def test_crud_service_proyect(self):
        created = ProyectService.create({'leader': 1, 'proyect_description': 'test description', 'title': 'test title', 'proyect_status': 'test state', 'created_by': 1})
        self.assertIsNotNone(created)
        page = ProyectService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)
