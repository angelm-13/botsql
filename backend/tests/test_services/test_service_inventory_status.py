from __future__ import annotations

from tests.conftest import BackendTestCase
from app.services.inventory_status_service import InventoryStatusService


class TestInventoryStatusService(BackendTestCase):
    def test_crud_service_inventory_status(self):
        created = InventoryStatusService.create({'inventory_status_code': 'ENTRADA', 'inventory_status_description': 'Entrada', 'color': '#22c55e', 'entity_scope': 'product', 'flow_scope': 'inventory', 'is_active': True, 'is_terminal': True, 'visible_to_other_departments': True, 'sort_order': 1, 'created_by': 1})
        self.assertIsNotNone(created)
        page = InventoryStatusService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)
