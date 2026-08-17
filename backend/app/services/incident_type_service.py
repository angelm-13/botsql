from app.models import IncidentType
from app.services.base_service import CrudService


class IncidentTypeService(CrudService):
    model = IncidentType
    primary_key = 'id_incident_type'
    entity_name = 'incident_type'
