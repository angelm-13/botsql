from datetime import date
from decimal import Decimal, InvalidOperation

from sqlalchemy import select

from app.models import PayrollParameter
from app.models.session import transaction_context
from app.services.base_service import CrudService
from app.utils.errors import AppError

# Claves que son porcentajes: no pueden pasar de 100.
CLAVES_PORCENTAJE = {
    "subsidy_pct", "imss_em_surplus_pct", "imss_em_cash_pct", "imss_em_pensioners_pct",
    "imss_iv_pct", "imss_cv_pct", "vacation_premium_pct",
}


def _fecha(valor, campo):
    if valor in (None, ""):
        return None
    if isinstance(valor, date):
        return valor
    try:
        return date.fromisoformat(str(valor)[:10])
    except ValueError as exc:
        raise AppError("errors.invalid_field", 400, {"field": campo}) from exc


def _numero(valor, campo):
    try:
        return Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise AppError("errors.invalid_field", 400, {"field": campo}) from exc


class PayrollParameterService(CrudService):
    """Cifras oficiales de nomina con vigencia (ver payroll_calculation_service).

    Tambien guarda las opciones de calculo de la empresa y su tabla de
    vacaciones (PARAMETROS_OPCIONALES), con la misma vigencia y fuente.

    Se valida aqui y no en la pantalla, para que valga igual por la API: solo
    las claves que el calculo conoce, valores dentro de rango y, para una misma
    clave, vigencias que no se enciman (si se enciman, el calculo no sabria
    cual usar).
    """

    model = PayrollParameter
    primary_key = 'id_payroll_parameter'
    entity_name = 'payroll_parameter'

    @classmethod
    def _validar(cls, datos: dict, excluir_id=None) -> None:
        from app.services.payroll_calculation_service import (OPCIONES, PARAMETROS_OPCIONALES,
                                                              PARAMETROS_REQUERIDOS, TABLA_DE_VACACIONES)
        claves = PARAMETROS_REQUERIDOS + PARAMETROS_OPCIONALES
        clave = str(datos.get("parameter_key") or "").strip()
        if clave not in claves:
            raise AppError("errors.invalid_field", 400, {"field": "parameter_key", "allowed": list(claves)})
        valor = _numero(datos.get("value"), "value")
        if valor < 0 or (clave in CLAVES_PORCENTAJE and valor > 100):
            raise AppError("errors.invalid_field", 400, {"field": "value"})
        # Una opcion es si (1) o no (0); los dias de vacaciones, enteros de 1 a 365.
        if clave in OPCIONES and valor not in (0, 1):
            raise AppError("errors.invalid_field", 400, {"field": "value", "allowed": [0, 1]})
        if clave in TABLA_DE_VACACIONES and (valor != valor.to_integral_value() or not 1 <= valor <= 365):
            raise AppError("errors.invalid_field", 400, {"field": "value", "reason": "whole_days"})
        desde = _fecha(datos.get("valid_from"), "valid_from")
        hasta = _fecha(datos.get("valid_to"), "valid_to")
        if desde is None:
            raise AppError("errors.invalid_field", 400, {"field": "valid_from"})
        if hasta is not None and hasta < desde:
            raise AppError("errors.invalid_field", 400, {"field": "valid_to"})
        with transaction_context() as db:
            for otro in db.scalars(
                select(PayrollParameter)
                .where(PayrollParameter.parameter_key == clave)
                .where(PayrollParameter.deletion_date.is_(None))
            ):
                if excluir_id is not None and str(otro.id_payroll_parameter) == str(excluir_id):
                    continue
                fin_otro = otro.valid_to or date.max
                if desde <= fin_otro and otro.valid_from <= (hasta or date.max):
                    raise AppError("errors.payroll_parameter_overlap", 409, {
                        "parameter_key": clave, "id_payroll_parameter": otro.id_payroll_parameter,
                        "valid_from": otro.valid_from.isoformat(),
                        "valid_to": otro.valid_to.isoformat() if otro.valid_to else None})

    @classmethod
    def create(cls, payload: dict, user_id: int | None = None):
        cls._validar(dict(payload or {}))
        return super().create(payload, user_id=user_id)

    @classmethod
    def update(cls, item_id, payload: dict, user_id: int | None = None):
        actual = cls.get(item_id)
        cls._validar({**actual, **dict(payload or {})}, excluir_id=item_id)
        return super().update(item_id, payload, user_id=user_id)
