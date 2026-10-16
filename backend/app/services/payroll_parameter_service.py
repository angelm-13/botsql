from app.models import PayrollParameter
from app.services.base_service import CrudService


class PayrollParameterService(CrudService):
    model = PayrollParameter
    primary_key = 'id_payroll_parameter'
    entity_name = 'payroll_parameter'
