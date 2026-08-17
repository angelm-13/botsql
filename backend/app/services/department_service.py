from app.models import Department
from app.services.base_service import CrudService


class DepartmentService(CrudService):
    model = Department
    primary_key = 'id_department'
    entity_name = 'department'
