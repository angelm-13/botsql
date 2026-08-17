from __future__ import annotations

from tests.conftest import BackendTestCase
from tests.model_factory import build_payload
from app.services.status_service import StatusService


class TestStatusService(BackendTestCase):
    def test_crud_service_status(self):
        created = StatusService.create(build_payload(StatusService, {'status_description': 'test name', 'category': 'test name', 'is_terminal': True, 'sort_order': 'mxn', 'created_by': 1}))
        self.assertIsNotNone(created)
        page = StatusService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)
