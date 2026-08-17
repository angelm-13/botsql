from app.models import Field
from app.services.base_service import CrudService


class FieldService(CrudService):
    model = Field
    primary_key = 'id_field'
    entity_name = 'field'
