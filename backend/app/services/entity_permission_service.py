from app.models import EntityPermission
from app.services.base_service import CrudService


class EntityPermissionService(CrudService):
    model = EntityPermission
    primary_key = 'id_entity_permission'
    entity_name = 'entity_permission'
