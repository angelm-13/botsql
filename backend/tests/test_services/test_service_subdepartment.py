from __future__ import annotations

from tests.conftest import BackendTestCase
from app.services.subdepartment_service import SubdepartmentService


class TestSubdepartmentService(BackendTestCase):
    def test_crud_service_subdepartment(self):
        created = SubdepartmentService.create({'subdepartment_description': 'test description', 'created_by': 1})
        self.assertIsNotNone(created)
        page = SubdepartmentService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)
