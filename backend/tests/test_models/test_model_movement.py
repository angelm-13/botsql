from __future__ import annotations

from datetime import datetime
from tests.conftest import BackendTestCase
from app.models.movement import Movement


class TestMovementModel(BackendTestCase):
    def test_create_serialize_summary_delete_movement(self):
        with transaction_context() as session:
            item = Movement(
            date='datetime.now()',
            type='income',
            amount=10.5,
            currency='mxn',
            type_exchange_rate=10.5,
            created_by=1
            )
            session.add(item)
            session.flush()
            data = item.serialize()
            self.assertIsInstance(data, dict)
            summary = item.serialize_summary()
            self.assertIsInstance(summary, dict)
            session.delete(item)
