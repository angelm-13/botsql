from app.models import PayrollPeriod
from app.models.session import transaction_context
from app.services.base_service import CrudService


class PayrollPeriodService(CrudService):
    model = PayrollPeriod
    primary_key = 'id_payroll_period'
    entity_name = 'payroll_period'

    # El estado del periodo (Abierto/Calculado/Cerrado) solo lo mueven calcular,
    # cerrar y reabrir (payroll_calculation_service.py); la captura generica no
    # lo escribe, y un periodo cerrado no se edita ni se borra.

    @staticmethod
    def _sin_campos_del_estado(payload: dict) -> dict:
        from app.services.payroll_calculation_service import CAMPOS_DEL_ESTADO
        return {k: v for k, v in dict(payload or {}).items() if k not in CAMPOS_DEL_ESTADO}

    @staticmethod
    def _exigir_no_cerrado(item_id) -> None:
        from app.services.payroll_calculation_service import exigir_periodo_no_cerrado
        with transaction_context() as db:
            exigir_periodo_no_cerrado(db, item_id)

    @classmethod
    def create(cls, payload: dict, user_id: int | None = None):
        return super().create(cls._sin_campos_del_estado(payload), user_id=user_id)

    @classmethod
    def update(cls, item_id, payload: dict, user_id: int | None = None):
        cls._exigir_no_cerrado(item_id)
        return super().update(item_id, cls._sin_campos_del_estado(payload), user_id=user_id)

    @classmethod
    def delete(cls, item_id, user_id: int | None = None):
        cls._exigir_no_cerrado(item_id)
        return super().delete(item_id, user_id=user_id)
