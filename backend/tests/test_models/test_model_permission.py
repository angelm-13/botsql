from __future__ import annotations

from datetime import datetime
from tests.conftest import BackendTestCase
from tests.model_factory import build_model
from app.models.session import transaction_context
from app.models.permission import Permission


class TestPermissionModel(BackendTestCase):
    def test_create_serialize_summary_delete_permission(self):
        with transaction_context() as session:
            item = build_model(Permission,
            created_by=1,
            authorized_by=1,
            permission_description='test permission description'
            )
            session.add(item)
            session.flush()
            data = item.serialize()
            self.assertIsInstance(data, dict)
            summary = item.serialize_summary()
            self.assertIsInstance(summary, dict)
            session.delete(item)
