from app.models import Brand
from app.services.base_service import CrudService


class BrandService(CrudService):
    model = Brand
    primary_key = 'id_brand'
    entity_name = 'brand'
