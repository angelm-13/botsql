from app.models import Proyect
from app.services.base_service import CrudService


class ProyectService(CrudService):
    model = Proyect
    primary_key = 'id_proyect'
    entity_name = 'proyect'
