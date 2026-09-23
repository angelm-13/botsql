from app.models import NmPermissionKpi
from app.services.base_service import CrudService


class NmPermissionKpiService(CrudService):
    model = NmPermissionKpi
    primary_key = 'id_nm_permission_kpi'
    entity_name = 'nm_permission_kpi'
