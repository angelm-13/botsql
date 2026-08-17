from app.models import PasswordResetToken
from app.services.base_service import CrudService


class PasswordResetTokenService(CrudService):
    model = PasswordResetToken
    primary_key = 'id_password_reset_token'
    entity_name = 'password_reset_token'
