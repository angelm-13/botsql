from app.models import PayrollIsrBracket
from app.services.base_service import CrudService


class PayrollIsrBracketService(CrudService):
    model = PayrollIsrBracket
    primary_key = 'id_payroll_isr_bracket'
    entity_name = 'payroll_isr_bracket'
