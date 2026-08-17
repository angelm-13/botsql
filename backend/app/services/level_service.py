from app.models import Level
from app.services.base_service import CrudService


class LevelService(CrudService):
    model = Level
    primary_key = 'id_level'
    entity_name = 'level'
