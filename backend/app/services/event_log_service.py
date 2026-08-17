from app.models import EventLog
from app.services.base_service import CrudService


class EventLogService(CrudService):
    model = EventLog
    primary_key = 'id_event_log'
    entity_name = 'event_log'
