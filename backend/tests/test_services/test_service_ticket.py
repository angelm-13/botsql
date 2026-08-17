from __future__ import annotations

from tests.conftest import BackendTestCase
from tests.model_factory import build_payload
from app.services.ticket_service import TicketService


class TestTicketService(BackendTestCase):
    def test_crud_service_ticket(self):
        created = TicketService.create(build_payload(TicketService, {'ticket_description': 'test description', 'ticket_status': 'test state', 'note': 'test respuesta', 'created_by': 1}))
        self.assertIsNotNone(created)
        page = TicketService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)
