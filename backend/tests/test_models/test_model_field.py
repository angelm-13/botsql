from __future__ import annotations

from datetime import datetime
from tests.conftest import BackendTestCase
from app.models.field import Field


class TestFieldModel(BackendTestCase):
    def test_create_serialize_summary_delete_field(self):
        with transaction_context() as session:
            item = Field(
            created_by=1,
            table_name='user',
            field_name='id_user'
            )
            session.add(item)
            session.flush()
            data = item.serialize()
            self.assertIsInstance(data, dict)
            summary = item.serialize_summary()
            self.assertIsInstance(summary, dict)
            session.delete(item)
