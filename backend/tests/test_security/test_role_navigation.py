from __future__ import annotations

import unittest

from app.models.entity_permission import EntityPermission
from app.routes.security import _catalog_for_actor


class TestRoleNavigation(unittest.TestCase):
    def test_entity_permission_serializes_navigation_configuration(self):
        permission = EntityPermission(
            id_entity_permission=7,
            id_permission=3,
            entity_name='invoice',
            control_type=15,
            menu_location='sidebar',
            menu_group='Contabilidad',
            menu_group_icon='file-text',
            menu_label='Facturas',
            menu_order=20,
            created_by=1,
        )

        self.assertEqual(permission.serialize(), {
            'id_entity_permission': 7,
            'id_permission': 3,
            'entity_name': 'invoice',
            'control_type': 15,
            'menu_location': 'sidebar',
            'menu_group': 'Contabilidad',
            'menu_group_icon': 'file-text',
            'menu_label': 'Facturas',
            'menu_order': 20,
        })

    def test_permission_catalog_includes_fieldless_restaurant_workspaces(self):
        catalog = _catalog_for_actor({'is_superuser': True})
        entities = {item['entity_name']: item for item in catalog['entities']}

        for entity_name in (
            'restaurant_waiter',
            'restaurant_cashier',
            'restaurant_kitchen',
            'restaurant_admin',
        ):
            self.assertIn(entity_name, entities)
            self.assertEqual(entities[entity_name]['domain'], 'restaurante')
            self.assertEqual(entities[entity_name]['permission_scope'], 'actions_only')
            self.assertEqual(entities[entity_name]['fields'], [])


if __name__ == '__main__':
    unittest.main()