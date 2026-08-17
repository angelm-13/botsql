from app.models import Subdepartment
from app.services.base_service import CrudService


class SubdepartmentService(CrudService):
    model = Subdepartment
    primary_key = 'id_subdepartment'
    entity_name = 'subdepartment'
