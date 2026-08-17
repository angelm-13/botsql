from app.models import Status
from app.services.base_service import CrudService


class StatusService(CrudService):
    model = Status
    primary_key = 'id_status'
    entity_name = 'status'
