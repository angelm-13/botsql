from __future__ import annotations

from datetime import datetime
from tests.conftest import BackendTestCase
from tests.model_factory import build_model
from app.models.session import transaction_context
from app.models.event_log import EventLog


class TestEventLogModel(BackendTestCase):
    def test_create_serialize_summary_delete_event_log(self):
        with transaction_context() as session:
            item = build_model(EventLog,
            table_name='user',
            field_name='user_id',
            action='create',
            before_value='test_before_value',
            after_value='test_after_value',
            created_by=1
            )
            session.add(item)
            session.flush()
            data = item.serialize()
            self.assertIsInstance(data, dict)
            summary = item.serialize_summary()
            self.assertIsInstance(summary, dict)
            session.delete(item)
