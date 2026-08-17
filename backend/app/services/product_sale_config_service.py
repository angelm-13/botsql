from app.models import ProductSaleConfig
from app.services.base_service import CrudService


class ProductSaleConfigService(CrudService):
    model = ProductSaleConfig
    primary_key = 'id_product_sale_config'
    entity_name = 'product_sale_config'
