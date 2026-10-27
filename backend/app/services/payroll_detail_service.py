from app.models import PayrollDetail
from app.models.session import transaction_context
from app.services.base_service import CrudService


class PayrollDetailService(CrudService):
    model = PayrollDetail
    primary_key = 'id_payroll_detail'
    entity_name = 'payroll_detail'

    # El detalle de un periodo cerrado no se da de alta, ni se edita, ni se
    # mueve a otro periodo, ni se borra (ver payroll_calculation_service.py).

    @classmethod
    def _exigir_periodos_no_cerrados(cls, item_id=None, payload=None) -> None:
        from app.services.payroll_calculation_service import exigir_periodo_no_cerrado
        with transaction_context() as db:
            if item_id is not None:
                try:
                    actual = db.get(PayrollDetail, int(item_id))
                except (TypeError, ValueError):
                    actual = None
                if actual is not None:
                    exigir_periodo_no_cerrado(db, actual.id_payroll_period)
            if payload and 'id_payroll_period' in payload:
                exigir_periodo_no_cerrado(db, payload.get('id_payroll_period'))

    @classmethod
    def create(cls, payload: dict, user_id: int | None = None):
        cls._exigir_periodos_no_cerrados(payload=payload)
        return super().create(payload, user_id=user_id)

    @classmethod
    def update(cls, item_id, payload: dict, user_id: int | None = None):
        cls._exigir_periodos_no_cerrados(item_id=item_id, payload=payload)
        return super().update(item_id, payload, user_id=user_id)

    @classmethod
    def delete(cls, item_id, user_id: int | None = None):
        cls._exigir_periodos_no_cerrados(item_id=item_id)
        return super().delete(item_id, user_id=user_id)
