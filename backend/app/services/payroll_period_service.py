from app.models import PayrollPeriod
from app.services.base_service import CrudService


class PayrollPeriodService(CrudService):
    model = PayrollPeriod
    primary_key = 'id_payroll_period'
    entity_name = 'payroll_period'
