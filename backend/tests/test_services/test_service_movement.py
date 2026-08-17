from __future__ import annotations

from tests.conftest import BackendTestCase
from app.services.movement_service import MovementService


class TestMovementService(BackendTestCase):
    def test_crud_service_movement(self):
        created = MovementService.create({'date': 'datetime.now()', 'type': 'income', 'amount': 10.5, 'currency': 'mxn', 'type_exchange_rate': 10.5, 'created_by': 1})
        self.assertIsNotNone(created)
        page = MovementService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)
