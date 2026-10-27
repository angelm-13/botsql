from app.models import PayrollDetail, PayrollMovement
from app.models.session import transaction_context
from app.services.base_service import CrudService


class PayrollMovementService(CrudService):
    model = PayrollMovement
    primary_key = 'id_payroll_movement'
    entity_name = 'payroll_movement'
    # Al recalcular, el movimiento anterior de SUELDO, ISR, IMSS... queda con
    # borrado logico. La lista solo muestra los vigentes (filtrado en SQL, asi el
    # total y la paginacion cuadran); los reemplazados siguen en la base y en la
    # bitacora para auditoria. Solo esta entidad de RH: las demas pantallas
    # genericas del sistema no cambian.
    solo_vigentes = True

    # Un movimiento de un periodo cerrado no se da de alta, ni se edita, ni se
    # pasa a otro detalle, ni se borra (ver payroll_calculation_service.py). El
    # periodo se llega por el detalle.

    @classmethod
    def _exigir_periodos_no_cerrados(cls, item_id=None, payload=None) -> None:
        from app.services.payroll_calculation_service import exigir_periodo_no_cerrado
        with transaction_context() as db:
            detalles = []
            if item_id is not None:
                try:
                    actual = db.get(PayrollMovement, int(item_id))
                except (TypeError, ValueError):
                    actual = None
                if actual is not None:
                    detalles.append(actual.id_payroll_detail)
            if payload and payload.get('id_payroll_detail') not in (None, ''):
                detalles.append(payload.get('id_payroll_detail'))
            for id_detalle in detalles:
                try:
                    detalle = db.get(PayrollDetail, int(id_detalle))
                except (TypeError, ValueError):
                    detalle = None
                if detalle is not None:
                    exigir_periodo_no_cerrado(db, detalle.id_payroll_period)

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
