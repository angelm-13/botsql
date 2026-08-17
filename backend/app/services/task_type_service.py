from app.models import TaskType
from app.services.base_service import CrudService


class TaskTypeService(CrudService):
    model = TaskType
    primary_key = 'id_task_type'
    entity_name = 'task_type'
