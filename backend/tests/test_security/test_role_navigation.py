from __future__ import annotations

import unittest

from app.models.entity_permission import EntityPermission


class TestRoleNavigation(unittest.TestCase):
    def test_entity_permission_serializes_navigation_configuration(self):
        permission = EntityPermission(
            id_entity_permission=7,
            id_permission=3,
            entity_name='invoice',
            control_type=15,
            menu_location='sidebar',
            menu_group='Contabilidad',
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
            'menu_label': 'Facturas',
            'menu_order': 20,
        })


if __name__ == '__main__':
    unittest.main()