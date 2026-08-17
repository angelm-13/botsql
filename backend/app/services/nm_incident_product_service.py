from app.models import NmIncidentProduct
from app.services.base_service import CrudService


class NmIncidentProductService(CrudService):
    model = NmIncidentProduct
    primary_key = 'id_nm_incident_product'
    entity_name = 'nm_incident_product'
