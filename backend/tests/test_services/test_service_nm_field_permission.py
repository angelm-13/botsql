from __future__ import annotations

from tests.conftest import BackendTestCase
from app.services.nm_field_permission_service import NmFieldPermissionService


class TestNmFieldPermissionService(BackendTestCase):
    def test_crud_service_nm_field_permission(self):
        created = NmFieldPermissionService.create({'control_type': '1', 'created_by': 1})
        self.assertIsNotNone(created)
        page = NmFieldPermissionService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)
