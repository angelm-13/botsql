from app.models import InvoiceMaterialService
from app.services.base_service import CrudService


class InvoiceMaterialServiceService(CrudService):
    model = InvoiceMaterialService
    primary_key = 'id_invoice_material_service'
    entity_name = 'invoice_material_service'
