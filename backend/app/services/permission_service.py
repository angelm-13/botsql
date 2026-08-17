from app.models import Permission
from app.services.base_service import CrudService


class PermissionService(CrudService):
    model = Permission
    primary_key = 'id_permission'
    entity_name = 'permission'
