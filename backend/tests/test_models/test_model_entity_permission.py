from __future__ import annotations

from datetime import datetime
from tests.conftest import BackendTestCase
from app.models.entity_permission import EntityPermission


class TestEntityPermissionModel(BackendTestCase):
    def test_create_serialize_summary_delete_entity_permission(self):
        with transaction_context() as session:
            item = EntityPermission(
            entity_name='bank',
            control_type='15',
            created_by=1
            )
            session.add(item)
            session.flush()
            data = item.serialize()
            self.assertIsInstance(data, dict)
            summary = item.serialize_summary()
            self.assertIsInstance(summary, dict)
            session.delete(item)
