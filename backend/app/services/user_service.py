from app.models import User
from app.services.base_service import CrudService


class UserService(CrudService):
    model = User
    primary_key = 'id_user'
    entity_name = 'user'
