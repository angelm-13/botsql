from app.models import PayrollConcept
from app.services.base_service import CrudService


class PayrollConceptService(CrudService):
    model = PayrollConcept
    primary_key = 'id_payroll_concept'
    entity_name = 'payroll_concept'
