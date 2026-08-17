from __future__ import annotations

from tests.conftest import BackendTestCase
from tests.model_factory import build_payload
from app.services.nm_incident_product_service import NmIncidentProductService


class TestNmIncidentProductService(BackendTestCase):
    def test_crud_service_nm_incident_product(self):
        created = NmIncidentProductService.create(build_payload(NmIncidentProductService, {'note': 'test note', 'quantity': 1, 'close_date': '2026-01-15T12:00:00', 'created_by': 1}))
        self.assertIsNotNone(created)
        page = NmIncidentProductService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)
