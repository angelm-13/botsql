from app.models import FiscalRecord
from app.services.base_service import CrudService


class FiscalRecordService(CrudService):
    model = FiscalRecord
    primary_key = 'id_fiscal_record'
    entity_name = 'fiscal_record'
