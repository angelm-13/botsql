"""Grupos de pago: cada grupo cobra con su periodicidad (semanal, catorcenal,
quincenal o mensual) y cada empleado pertenece a uno, con vigencia.

Un periodo de nomina de un grupo calcula solo a sus empleados y usa la tarifa
del ISR de su periodicidad (payroll_tax_rules.tabla_para_periodicidad). Quien
no tiene grupo asignado cae en el grupo por omision ("General: quincenal",
sembrado por la migracion 20261028100000), asi una empresa que no usa grupos
sigue igual. Los periodos de antes de los grupos (sin `id_payroll_group`)
calculan a todos con la tarifa por dias, como siempre.

Los servicios de las dos tablas viven aqui; employee_payroll_group_service.py
lo reexporta para la ruta generica.
"""
from __future__ import annotations

import calendar
from datetime import date, timedelta

from sqlalchemy import select

from app.models import EmployeePayrollGroup, PayrollGroup, PayrollPeriod, User
from app.models.payroll_group import MENSUAL, PERIODICIDADES, QUINCENAL, SEMANAL
from app.models.session import transaction_context
from app.services import payroll_tax_rules as ley
from app.services.base_service import CrudService
from app.services.work_schedule_service import _entero, _fecha
from app.utils.errors import AppError
from app.utils.tiempo import ahora_utc


def _grupo_vivo(db, id_payroll_group) -> PayrollGroup:
    try:
        grupo = db.get(PayrollGroup, int(id_payroll_group))
    except (TypeError, ValueError):
        grupo = None
    if grupo is None or grupo.deletion_date is not None:
        raise AppError("errors.invalid_field", 400, {"field": "id_payroll_group"})
    return grupo


class PayrollGroupService(CrudService):
    model = PayrollGroup
    primary_key = 'id_payroll_group'
    entity_name = 'payroll_group'

    @classmethod
    def _validar(cls, datos: dict) -> None:
        if not str(datos.get("group_name") or "").strip():
            raise AppError("errors.invalid_field", 400, {"field": "group_name"})
        if datos.get("pay_frequency") not in PERIODICIDADES:
            raise AppError("errors.invalid_field", 400, {"field": "pay_frequency", "allowed": list(PERIODICIDADES)})

    @staticmethod
    def _quitar_otro_por_omision(excepto=None) -> None:
        """Solo un grupo es el de por omision: marcar uno desmarca al anterior."""
        with transaction_context() as db:
            for otro in db.scalars(select(PayrollGroup).where(PayrollGroup.is_default.is_(True))
                                   .where(PayrollGroup.deletion_date.is_(None))):
                if excepto is None or str(otro.id_payroll_group) != str(excepto):
                    otro.is_default = False

    @classmethod
    def create(cls, payload: dict, user_id: int | None = None):
        payload = dict(payload or {})
        cls._validar(payload)
        creado = super().create(payload, user_id=user_id)
        if creado.get("is_default"):
            cls._quitar_otro_por_omision(excepto=creado["id_payroll_group"])
        return creado

    @classmethod
    def update(cls, item_id, payload: dict, user_id: int | None = None):
        payload = dict(payload or {})
        actual = cls.get(item_id)
        cls._validar({**actual, **payload})
        if "is_default" in payload:
            if actual.get("is_default") and not payload["is_default"]:
                # Siempre hay un grupo por omision: se cambia marcando otro.
                raise AppError("errors.payroll_group_default_required", 409, {"id_payroll_group": int(item_id)})
        actualizado = super().update(item_id, payload, user_id=user_id)
        if actualizado.get("is_default"):
            cls._quitar_otro_por_omision(excepto=item_id)
        return actualizado

    @classmethod
    def delete(cls, item_id, user_id: int | None = None):
        actual = cls.get(item_id)
        if actual.get("is_default"):
            raise AppError("errors.payroll_group_default_required", 409, {"id_payroll_group": int(item_id)})
        with transaction_context() as db:
            asignados = db.scalars(select(EmployeePayrollGroup)
                                   .where(EmployeePayrollGroup.id_payroll_group == int(item_id))
                                   .where(EmployeePayrollGroup.deletion_date.is_(None))).first()
            if asignados is not None:
                raise AppError("errors.payroll_group_in_use", 409, {"id_payroll_group": int(item_id)})
        return super().delete(item_id, user_id=user_id)


class EmployeePayrollGroupService(CrudService):
    """Grupo de pago de un empleado; las vigencias de una persona no se enciman."""

    model = EmployeePayrollGroup
    primary_key = 'id_employee_payroll_group'
    entity_name = 'employee_payroll_group'

    @classmethod
    def _validar(cls, datos: dict, excluir_id=None) -> None:
        id_user = _entero(datos.get("id_user"), "id_user")
        desde = _fecha(datos.get("valid_from"), "valid_from")
        hasta = _fecha(datos.get("valid_to"), "valid_to", opcional=True)
        if hasta is not None and hasta < desde:
            raise AppError("errors.invalid_field", 400, {"field": "valid_to"})
        with transaction_context() as db:
            empleado = db.get(User, id_user)
            if empleado is None or empleado.deletion_date is not None or not empleado.is_employee:
                raise AppError("errors.invalid_field", 400, {"field": "id_user", "reason": "not_employee"})
            _grupo_vivo(db, datos.get("id_payroll_group"))
            for otro in db.scalars(select(EmployeePayrollGroup)
                                   .where(EmployeePayrollGroup.id_user == id_user)
                                   .where(EmployeePayrollGroup.deletion_date.is_(None))):
                if excluir_id is not None and str(otro.id_employee_payroll_group) == str(excluir_id):
                    continue
                if desde <= (otro.valid_to or date.max) and otro.valid_from <= (hasta or date.max):
                    raise AppError("errors.employee_payroll_group_overlap", 409, {
                        "id_employee_payroll_group": otro.id_employee_payroll_group,
                        "valid_from": otro.valid_from.isoformat(),
                        "valid_to": otro.valid_to.isoformat() if otro.valid_to else None})

    @classmethod
    def create(cls, payload: dict, user_id: int | None = None):
        cls._validar(dict(payload or {}))
        return super().create(payload, user_id=user_id)

    @classmethod
    def update(cls, item_id, payload: dict, user_id: int | None = None):
        cls._validar({**cls.get(item_id), **dict(payload or {})}, excluir_id=item_id)
        return super().update(item_id, payload, user_id=user_id)


# --- reglas que usa el calculo de la nomina ----------------------------------

def grupo_del_periodo(db, periodo: PayrollPeriod) -> PayrollGroup | None:
    """El grupo del periodo; None si es un periodo de antes de los grupos."""
    if periodo.id_payroll_group is None:
        return None
    return _grupo_vivo(db, periodo.id_payroll_group)


def exigir_largo_del_periodo(grupo: PayrollGroup, inicio: date, fin: date) -> None:
    """Un periodo semanal dura 7 dias, uno catorcenal 14, una quincena de 13 a 16 y un mes de 28 a 31."""
    minimo, maximo = ley.DIAS_POR_PERIODICIDAD[grupo.pay_frequency]
    dias = (fin - inicio).days + 1
    if not minimo <= dias <= maximo:
        raise AppError("errors.payroll_period_length", 400, {
            "field": "period_end", "pay_frequency": grupo.pay_frequency, "days": dias,
            "min_days": minimo, "max_days": maximo})


def empleados_del_grupo(db, grupo: PayrollGroup, al_dia: date, empleados) -> list:
    """Los `empleados` que al `al_dia` pertenecen a `grupo`. Quien no tiene grupo
    asignado ese dia pertenece al grupo por omision."""
    ids = [e.id_user for e in empleados]
    asignado = {}
    if ids:
        for fila in db.scalars(select(EmployeePayrollGroup)
                               .where(EmployeePayrollGroup.id_user.in_(ids))
                               .where(EmployeePayrollGroup.deletion_date.is_(None))
                               .where(EmployeePayrollGroup.valid_from <= al_dia)
                               .where((EmployeePayrollGroup.valid_to.is_(None))
                                      | (EmployeePayrollGroup.valid_to >= al_dia))):
            asignado[fila.id_user] = fila.id_payroll_group
    return [e for e in empleados
            if asignado.get(e.id_user) == grupo.id_payroll_group
            or (e.id_user not in asignado and grupo.is_default)]


def _fin_del_periodo(periodicidad: str, inicio: date) -> date:
    if periodicidad == QUINCENAL:
        return inicio.replace(day=15) if inicio.day <= 15 else \
            inicio.replace(day=calendar.monthrange(inicio.year, inicio.month)[1])
    if periodicidad == MENSUAL:
        return inicio.replace(day=calendar.monthrange(inicio.year, inicio.month)[1])
    minimo, _ = ley.DIAS_POR_PERIODICIDAD[periodicidad]
    return inicio + timedelta(days=minimo - 1)


def _primer_inicio(periodicidad: str, hoy: date) -> date:
    """Sin periodos anteriores: el periodo en curso. La semana empieza en lunes,
    la quincena el 1 o el 16 y el mes el 1; la catorcena empieza hoy."""
    if periodicidad == SEMANAL:
        return hoy - timedelta(days=hoy.weekday())
    if periodicidad == QUINCENAL:
        return hoy.replace(day=1 if hoy.day <= 15 else 16)
    if periodicidad == MENSUAL:
        return hoy.replace(day=1)
    return hoy


def siguiente_periodo(id_payroll_group, hoy: date | None = None) -> dict:
    """Las fechas que siguen para un grupo: el dia despues de su ultimo periodo,
    con el largo de su periodicidad. Es una propuesta: RH la puede cambiar."""
    with transaction_context() as db:
        grupo = _grupo_vivo(db, id_payroll_group)
        ultimo = db.scalars(select(PayrollPeriod)
                            .where(PayrollPeriod.id_payroll_group == grupo.id_payroll_group)
                            .where(PayrollPeriod.deletion_date.is_(None))
                            .where(PayrollPeriod.period_end.is_not(None))
                            .order_by(PayrollPeriod.period_end.desc())).first()
        inicio = ultimo.period_end + timedelta(days=1) if ultimo else \
            _primer_inicio(grupo.pay_frequency, hoy or ahora_utc().date())
        fin = _fin_del_periodo(grupo.pay_frequency, inicio)
        return {"id_payroll_group": grupo.id_payroll_group, "pay_frequency": grupo.pay_frequency,
                "period_start": inicio.isoformat(), "period_end": fin.isoformat(),
                "payment_date": fin.isoformat()}
