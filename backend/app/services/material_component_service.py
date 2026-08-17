from app.models import MaterialComponent
from app.services.base_service import CrudService


class MaterialComponentService(CrudService):
    model = MaterialComponent
    primary_key = 'id_material_component'
    entity_name = 'material_component'
