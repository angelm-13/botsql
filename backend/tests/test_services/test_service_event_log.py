from __future__ import annotations

from tests.conftest import BackendTestCase
from tests.model_factory import build_payload
from app.services.event_log_service import EventLogService


class TestEventLogService(BackendTestCase):
    def test_crud_service_event_log(self):
        created = EventLogService.create(build_payload(EventLogService, {'table_name': 'user', 'field_name': 'user_id', 'action': 'create', 'before_value': 'test_before_value', 'after_value': 'test_after_value', 'created_by': 1}))
        self.assertIsNotNone(created)
        page = EventLogService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)
