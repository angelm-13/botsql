from app.models import Incident
from app.services.base_service import CrudService


class IncidentService(CrudService):
    model = Incident
    primary_key = 'id_incident'
    entity_name = 'incident'
