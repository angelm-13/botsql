from __future__ import annotations

from datetime import datetime
from tests.conftest import BackendTestCase
from app.models.ticket import Ticket


class TestTicketModel(BackendTestCase):
    def test_create_serialize_summary_delete_ticket(self):
        with transaction_context() as session:
            item = Ticket(
            ticket_description='test description',
            ticket_status='test state',
            note='test respuesta',
            created_by=1
            )
            session.add(item)
            session.flush()
            data = item.serialize()
            self.assertIsInstance(data, dict)
            summary = item.serialize_summary()
            self.assertIsInstance(summary, dict)
            session.delete(item)
