from __future__ import annotations

import unittest

from app.models.entity_permission import EntityPermission
from app.modules.registry import ENTIDAD_A_MODULO
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
            self.assertEqual(entities[entity_name]['domain'], 'restaurant')
            self.assertEqual(entities[entity_name]['permission_scope'], 'actions_only')
            self.assertEqual(entities[entity_name]['fields'], [])

    def test_the_catalog_covers_every_entity_the_registry_declares(self):
        """El catalogo del gestor de roles es una foto a mano, no una consulta.

        `_PERMISSION_CATALOG` (en `security.py`) se escribio una vez y desde
        entonces nadie lo vuelve a llenar cuando se agrega una entidad al
        registro: paso con Documentos, Laboratorio y Logistica -sembradas y
        con permiso real en la base, pero invisibles en el Gestor de roles y
        permisos, asi que ningun rol podia dárselas ni quitárselas- y volvio a
        pasar con `appointment`, las cuatro de `kpis` y `material_attribute`.

        Sin esta prueba, la proxima entidad que alguien declare en el
        registro se pierde en silencio hasta que un cliente real note que no
        puede quitar un modulo desde el Gestor.
        """
        catalog = _catalog_for_actor({'is_superuser': True})
        en_catalogo = {item['entity_name'] for item in catalog['entities']}
        faltantes = sorted(set(ENTIDAD_A_MODULO) - en_catalogo)

        self.assertEqual(
            [], faltantes,
            "Estas entidades estan declaradas en app/modules/registry.py pero "
            "no aparecen en el catalogo del Gestor de roles y permisos, asi "
            "que ningun rol puede concederselas ni quitarselas desde ahi: "
            + ", ".join(faltantes),
        )


if __name__ == '__main__':
    unittest.main()