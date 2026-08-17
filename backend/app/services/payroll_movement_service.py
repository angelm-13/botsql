from app.models import PayrollMovement
from app.services.base_service import CrudService


class PayrollMovementService(CrudService):
    model = PayrollMovement
    primary_key = 'id_payroll_movement'
    entity_name = 'payroll_movement'
