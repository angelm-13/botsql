from app.models import FiscalAccount
from app.services.base_service import CrudService


class FiscalAccountService(CrudService):
    model = FiscalAccount
    primary_key = 'id_fiscal_account'
    entity_name = 'fiscal_account'
