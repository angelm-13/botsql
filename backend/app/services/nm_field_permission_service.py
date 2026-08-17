from app.models import NmFieldPermission
from app.services.base_service import CrudService


class NmFieldPermissionService(CrudService):
    model = NmFieldPermission
    primary_key = 'id_nm_field_permission'
    entity_name = 'nm_field_permission'
