from app.models import Material
from app.services.base_service import CrudService


class MaterialService(CrudService):
    model = Material
    primary_key = 'id_material'
    entity_name = 'material'
