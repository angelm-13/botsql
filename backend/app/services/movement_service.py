from app.models import Movement
from app.services.base_service import CrudService


class MovementService(CrudService):
    model = Movement
    primary_key = 'id_movement'
    entity_name = 'movement'
