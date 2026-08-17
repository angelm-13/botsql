from app.models import IncidentDetail
from app.services.base_service import CrudService


class IncidentDetailService(CrudService):
    model = IncidentDetail
    primary_key = 'id_incident_detail'
    entity_name = 'incident_detail'
