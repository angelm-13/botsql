from app.models import CustomerSupplier
from app.services.base_service import CrudService


class CustomerSupplierService(CrudService):
    model = CustomerSupplier
    primary_key = 'id_customer_supplier'
    entity_name = 'customer_supplier'
