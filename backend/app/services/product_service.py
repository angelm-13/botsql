from app.models import Product
from app.services.base_service import CrudService


class ProductService(CrudService):
    model = Product
    primary_key = 'id_product'
    entity_name = 'product'
