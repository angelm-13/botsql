from __future__ import annotations

from tests.conftest import BackendTestCase
from tests.model_factory import build_payload
from app.services.permission_service import PermissionService


class TestPermissionService(BackendTestCase):
    def test_crud_service_permission(self):
        created = PermissionService.create(build_payload(PermissionService, {'created_by': 1, 'authorized_by': 1, 'permission_description': 'test permission description'}))
        self.assertIsNotNone(created)
        page = PermissionService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)
