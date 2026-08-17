from app.models import TaskNote
from app.services.base_service import CrudService


class TaskNoteService(CrudService):
    model = TaskNote
    primary_key = 'id_task_note'
    entity_name = 'task_note'
