from __future__ import annotations

from datetime import datetime
from tests.conftest import BackendTestCase
from app.models.inventory_status import InventoryStatus


class TestInventoryStatusModel(BackendTestCase):
    def test_create_serialize_summary_delete_inventory_status(self):
        with transaction_context() as session:
            item = InventoryStatus(
            inventory_status_code='ENTRADA',
            inventory_status_description='Entrada',
            color='#22c55e',
            entity_scope='product',
            flow_scope='inventory',
            is_active=True,
            is_terminal=True,
            visible_to_other_departments=True,
            sort_order=1,
            created_by=1
            )
            session.add(item)
            session.flush()
            data = item.serialize()
            self.assertIsInstance(data, dict)
            summary = item.serialize_summary()
            self.assertIsInstance(summary, dict)
            session.delete(item)
