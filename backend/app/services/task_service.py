from app.models import Task
from app.services.base_service import CrudService


class TaskService(CrudService):
    model = Task
    primary_key = 'id_task'
    entity_name = 'task'
