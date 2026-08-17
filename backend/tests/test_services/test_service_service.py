from __future__ import annotations

from tests.conftest import BackendTestCase
from tests.model_factory import build_payload
from app.services.service_service import ServiceService


class TestServiceService(BackendTestCase):
    def test_crud_service_service(self):
        created = ServiceService.create(build_payload(ServiceService, {'service_description': 'test description', 'average_time_cost': 10.5, 'created_by': 1}))
        self.assertIsNotNone(created)
        page = ServiceService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)
