from app.models import UserMfa
from app.services.base_service import CrudService


class UserMfaService(CrudService):
    model = UserMfa
    primary_key = 'id_user_mfa'
    entity_name = 'user_mfa'
