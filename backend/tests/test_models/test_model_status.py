from __future__ import annotations

from datetime import datetime
from tests.conftest import BackendTestCase
from app.models.status import Status


class TestStatusModel(BackendTestCase):
    def test_create_serialize_summary_delete_status(self):
        with transaction_context() as session:
            item = Status(
            status_description='test name',
            category='test name',
            is_terminal=True,
            sort_order='mxn',
            created_by=1
            )
            session.add(item)
            session.flush()
            data = item.serialize()
            self.assertIsInstance(data, dict)
            summary = item.serialize_summary()
            self.assertIsInstance(summary, dict)
            session.delete(item)
