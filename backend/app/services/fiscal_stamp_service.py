from app.models import FiscalStamp
from app.services.base_service import CrudService


class FiscalStampService(CrudService):
    model = FiscalStamp
    primary_key = 'id_fiscal_stamp'
    entity_name = 'fiscal_stamp'
