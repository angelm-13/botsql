from __future__ import annotations

from tests.conftest import BackendTestCase
from tests.model_factory import build_payload
from app.services.movement_service import MovementService


class TestMovementService(BackendTestCase):
    def test_crud_service_movement(self):
        created = MovementService.create(build_payload(MovementService, {'date': '2026-01-15T12:00:00', 'type': 'income', 'amount': 10.5, 'currency': 'mxn', 'type_exchange_rate': 10.5, 'created_by': 1}))
        self.assertIsNotNone(created)
        page = MovementService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)
