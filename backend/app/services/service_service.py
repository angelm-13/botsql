from app.models import Service
from app.services.base_service import CrudService


class ServiceService(CrudService):
    model = Service
    primary_key = 'id_service'
    entity_name = 'service'
