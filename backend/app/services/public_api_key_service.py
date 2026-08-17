from app.models import PublicApiKey
from app.services.base_service import CrudService


class PublicApiKeyService(CrudService):
    model = PublicApiKey
    primary_key = 'id_public_api_key'
    entity_name = 'public_api_key'
