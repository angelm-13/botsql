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

    def test_granting_again_a_removed_permission_reuses_the_same_row(self):
        base = build_payload(EntityPermissionService, {
            'entity_name': 'task_type', 'created_by': 1,
            'scope_create': 0, 'scope_read': 4, 'scope_update': 0, 'scope_delete': 0,
        })
        first = EntityPermissionService.create(dict(base))
        EntityPermissionService.delete(first['id_entity_permission'])

        again = EntityPermissionService.create(dict(base, scope_create=4, scope_update=4))

        self.assertEqual(again['id_entity_permission'], first['id_entity_permission'])
        self.assertEqual((again['scope_create'], again['scope_read'], again['scope_update'], again['scope_delete']),
                         (4, 4, 4, 0))
        vigentes = EntityPermissionService.list(page=1, per_page=500, filters={'entity_name': 'task_type'})
        self.assertEqual(len([i for i in vigentes['items']
                              if i['id_permission'] == first['id_permission']]), 1)
