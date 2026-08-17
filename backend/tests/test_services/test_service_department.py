from __future__ import annotations

from tests.conftest import BackendTestCase
from app.services.department_service import DepartmentService


class TestDepartmentService(BackendTestCase):
    def test_crud_service_department(self):
        created = DepartmentService.create({'department_description': 'test description', 'created_by': 1})
        self.assertIsNotNone(created)
        page = DepartmentService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)
