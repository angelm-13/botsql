from decimal import Decimal, InvalidOperation

from sqlalchemy import select

from app.models import PayrollIsrBracket
from app.models.session import transaction_context
from app.services.base_service import CrudService
from app.utils.errors import AppError

# Tablas que el calculo sabe usar (payroll_tax_rules.tabla_para_dias).
PERIODICIDADES = (1, 7, 10, 15, 30)


def _numero(valor, campo, opcional=False):
    if opcional and valor in (None, ""):
        return None
    try:
        return Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise AppError("errors.invalid_field", 400, {"field": campo}) from exc


class PayrollIsrBracketService(CrudService):
    """Tramos de la tarifa del ISR (ver payroll_tax_rules).

    Se valida aqui para que valga igual por la API: una periodicidad que el
    calculo conoce, limites y porcentaje en rango y, dentro de una misma tabla
    (año y periodicidad), tramos que no se enciman.
    """

    model = PayrollIsrBracket
    primary_key = 'id_payroll_isr_bracket'
    entity_name = 'payroll_isr_bracket'

    @classmethod
    def _validar(cls, datos: dict, excluir_id=None) -> None:
        try:
            dias = int(datos.get("period_days"))
            anio = int(datos.get("valid_year"))
        except (TypeError, ValueError) as exc:
            raise AppError("errors.invalid_field", 400, {"field": "period_days"}) from exc
        if dias not in PERIODICIDADES:
            raise AppError("errors.invalid_field", 400, {"field": "period_days", "allowed": list(PERIODICIDADES)})
        if not 2000 <= anio <= 2100:
            raise AppError("errors.invalid_field", 400, {"field": "valid_year"})
        inferior = _numero(datos.get("lower_limit"), "lower_limit")
        superior = _numero(datos.get("upper_limit"), "upper_limit", opcional=True)
        cuota = _numero(datos.get("fixed_fee"), "fixed_fee")
        tasa = _numero(datos.get("rate_pct"), "rate_pct")
        if inferior < 0:
            raise AppError("errors.invalid_field", 400, {"field": "lower_limit"})
        if superior is not None and superior <= inferior:
            raise AppError("errors.invalid_field", 400, {"field": "upper_limit"})
        if cuota < 0:
            raise AppError("errors.invalid_field", 400, {"field": "fixed_fee"})
        if not 0 <= tasa <= 100:
            raise AppError("errors.invalid_field", 400, {"field": "rate_pct"})
        infinito = Decimal("1e18")
        with transaction_context() as db:
            for otro in db.scalars(
                select(PayrollIsrBracket)
                .where(PayrollIsrBracket.period_days == dias)
                .where(PayrollIsrBracket.valid_year == anio)
                .where(PayrollIsrBracket.deletion_date.is_(None))
            ):
                if excluir_id is not None and str(otro.id_payroll_isr_bracket) == str(excluir_id):
                    continue
                tope_otro = otro.upper_limit if otro.upper_limit is not None else infinito
                if inferior <= tope_otro and otro.lower_limit <= (superior if superior is not None else infinito):
                    raise AppError("errors.payroll_isr_bracket_overlap", 409, {
                        "id_payroll_isr_bracket": otro.id_payroll_isr_bracket,
                        "lower_limit": float(otro.lower_limit),
                        "upper_limit": float(otro.upper_limit) if otro.upper_limit is not None else None})

    @classmethod
    def create(cls, payload: dict, user_id: int | None = None):
        cls._validar(dict(payload or {}))
        return super().create(payload, user_id=user_id)

    @classmethod
    def update(cls, item_id, payload: dict, user_id: int | None = None):
        actual = cls.get(item_id)
        cls._validar({**actual, **dict(payload or {})}, excluir_id=item_id)
        return super().update(item_id, payload, user_id=user_id)
