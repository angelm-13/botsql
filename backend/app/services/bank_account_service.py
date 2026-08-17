from app.models import BankAccount
from app.services.base_service import CrudService


class BankAccountService(CrudService):
    model = BankAccount
    primary_key = 'id_bank_account'
    entity_name = 'bank_account'
