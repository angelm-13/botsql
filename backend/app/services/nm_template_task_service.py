from app.models import NmTemplateTask
from app.services.base_service import CrudService


class NmTemplateTaskService(CrudService):
    model = NmTemplateTask
    primary_key = 'id_nm_template_task'
    entity_name = 'nm_template_task'
