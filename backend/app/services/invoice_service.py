from app.models import Invoice
from app.services.base_service import CrudService


class InvoiceService(CrudService):
    model = Invoice
    primary_key = 'id_invoice'
    entity_name = 'invoice'
