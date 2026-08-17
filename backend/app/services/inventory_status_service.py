from app.models import InventoryStatus
from app.services.base_service import CrudService


class InventoryStatusService(CrudService):
    model = InventoryStatus
    primary_key = 'id_inventory_status'
    entity_name = 'inventory_status'
