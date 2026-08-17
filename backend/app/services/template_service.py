from app.models import Template
from app.services.base_service import CrudService


class TemplateService(CrudService):
    model = Template
    primary_key = 'id_template'
    entity_name = 'template'
