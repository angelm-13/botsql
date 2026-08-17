from app.models import Bank
from app.services.base_service import CrudService


class BankService(CrudService):
    model = Bank
    primary_key = 'id_bank'
    entity_name = 'bank'
