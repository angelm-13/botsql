from app.models import Ticket
from app.services.base_service import CrudService


class TicketService(CrudService):
    model = Ticket
    primary_key = 'id_ticket'
    entity_name = 'ticket'
