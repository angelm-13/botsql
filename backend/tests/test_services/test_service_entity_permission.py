from __future__ import annotations

from tests.conftest import BackendTestCase
from tests.model_factory import build_payload
from app.services.entity_permission_service import EntityPermissionService


class TestEntityPermissionService(BackendTestCase):
    def test_crud_service_entity_permission(self):
        created = EntityPermissionService.create(build_payload(EntityPermissionService, {
            'entity_name': 'bank',
            'scope_create': 4, 'scope_read': 4, 'scope_update': 4, 'scope_delete': 4,
            'created_by': 1,
        }))
        self.assertIsNotNone(created)
        page = EntityPermissionService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)
