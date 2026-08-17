from app.models import PayrollDetail
from app.services.base_service import CrudService


class PayrollDetailService(CrudService):
    model = PayrollDetail
    primary_key = 'id_payroll_detail'
    entity_name = 'payroll_detail'
