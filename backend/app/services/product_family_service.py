from app.models import ProductFamily
from app.services.base_service import CrudService


class ProductFamilyService(CrudService):
    model = ProductFamily
    primary_key = 'id_product_family'
    entity_name = 'product_family'
