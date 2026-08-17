from app.models import Unit
from app.services.base_service import CrudService


class UnitService(CrudService):
    model = Unit
    primary_key = 'id_unit'
    entity_name = 'unit'
