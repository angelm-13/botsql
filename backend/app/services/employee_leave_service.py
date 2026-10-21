"""Vacaciones, permisos e incapacidades (employee_leave) y el saldo de vacaciones.

Que dia de una ausencia es falta y cual se paga lo decide
services/attendance_rules.py. Aqui viven las reglas de captura, validadas en
el backend para que valgan igual por la API:

* Las ausencias de un mismo empleado no se enciman.
* No se registra, edita ni borra una ausencia cuyas fechas caigan en un periodo
  de nomina cerrado: el recibo ya pagado no debe quedar distinto de lo
  registrado (decision de RH, 2026-10-21).
* Vacaciones (LFT art. 76): necesitan fecha de ingreso, no hay antes del primer
  año, no cruzan el aniversario y no pasan del saldo. Solo se descuentan los
  dias laborables del horario del empleado, asi que necesita horario asignado
  en todo el rango.

Saldo de vacaciones: al cumplir cada año de servicio le tocan los dias de ese
año; disponibles = los que le tocan - los tomados desde su ultimo aniversario.
Los dias no usados del año anterior no se acumulan (decision de RH, 2026-10-21).
"""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select

from app.models import EmployeeLeave, PayrollPeriod, User
from app.models.employee_leave import TIPOS_DE_AUSENCIA
from app.models.session import transaction_context
from app.services import payroll_tax_rules as ley
from app.services.base_service import CrudService
from app.services.work_schedule_service import _entero, _fecha
from app.utils.errors import AppError
from app.utils.tiempo import ahora_negocio

VACACIONES = "vacation"


def _aniversario(ingreso: date, anios: int) -> date:
    try:
        return ingreso.replace(year=ingreso.year + anios)
    except ValueError:  # 29 de febrero en un año no bisiesto
        return date(ingreso.year + anios, 2, 28)


def ano_de_servicio(ingreso: date, al_dia: date) -> tuple[int, date, date]:
    """(años cumplidos, inicio y fin del año de servicio en curso) `al_dia`."""
    anios = ley.anios_cumplidos(ingreso, al_dia)
    return anios, _aniversario(ingreso, anios), _aniversario(ingreso, anios + 1) - timedelta(days=1)


def dias_laborables(db, id_user: int, desde: date, hasta: date) -> tuple[int, bool]:
    """(dias laborables de su horario en el rango, si todo el rango tiene horario)."""
    from app.services.attendance_record_service import asistencia_por_empleado
    dias = asistencia_por_empleado(db, desde, hasta, ids=[id_user]).get(id_user, [])
    return sum(d.laboral for d in dias), bool(dias) and all(d.con_horario for d in dias)


def _vacaciones_tomadas(db, id_user: int, desde: date, hasta: date, excluir_id=None) -> int:
    total = 0
    for v in db.scalars(select(EmployeeLeave)
                        .where(EmployeeLeave.id_user == id_user)
                        .where(EmployeeLeave.leave_type == VACACIONES)
                        .where(EmployeeLeave.deletion_date.is_(None))
                        .where(EmployeeLeave.start_date <= hasta)
                        .where(EmployeeLeave.end_date >= desde)):
        if excluir_id is not None and str(v.id_employee_leave) == str(excluir_id):
            continue
        total += dias_laborables(db, id_user, max(v.start_date, desde), min(v.end_date, hasta))[0]
    return total


def saldo_de_vacaciones(db, empleado: User, al_dia: date, excluir_id=None) -> dict:
    ingreso = empleado.hire_date
    if not ingreso or ingreso > al_dia:
        return {"id_user": empleado.id_user, "full_name": empleado.full_name or "", "hire_date": None,
                "service_years": 0, "entitled": 0, "taken": 0, "available": 0,
                "year_start": None, "year_end": None}
    anios, inicio, fin = ano_de_servicio(ingreso, al_dia)
    derecho = ley.dias_de_vacaciones(anios - 1) if anios >= 1 else 0
    tomadas = _vacaciones_tomadas(db, empleado.id_user, inicio, fin, excluir_id) if anios >= 1 else 0
    return {"id_user": empleado.id_user, "full_name": empleado.full_name or "", "hire_date": ingreso.isoformat(),
            "service_years": anios, "entitled": derecho, "taken": tomadas, "available": max(derecho - tomadas, 0),
            "year_start": inicio.isoformat(), "year_end": fin.isoformat()}


def saldos() -> list[dict]:
    """Saldo de vacaciones de cada empleado al dia de hoy (hora del negocio)."""
    hoy = ahora_negocio().date()
    with transaction_context() as db:
        empleados = db.scalars(select(User)
                               .where(User.deletion_date.is_(None))
                               .where(User.is_employee.is_(True))
                               .order_by(User.full_name)).all()
        return [saldo_de_vacaciones(db, e, hoy) for e in empleados]


def _exigir_fuera_de_periodo_cerrado(db, desde: date, hasta: date) -> None:
    cerrado = db.scalars(select(PayrollPeriod)
                         .where(PayrollPeriod.deletion_date.is_(None))
                         .where(PayrollPeriod.period_state == "closed")
                         .where(PayrollPeriod.period_start <= hasta)
                         .where(PayrollPeriod.period_end >= desde)).first()
    if cerrado is not None:
        raise AppError("errors.payroll_period_closed", 409, {"id_payroll_period": cerrado.id_payroll_period})


class EmployeeLeaveService(CrudService):
    model = EmployeeLeave
    primary_key = 'id_employee_leave'
    entity_name = 'employee_leave'

    @classmethod
    def _validar(cls, datos: dict, excluir_id=None) -> None:
        id_user = _entero(datos.get("id_user"), "id_user")
        tipo = str(datos.get("leave_type") or "")
        if tipo not in TIPOS_DE_AUSENCIA:
            raise AppError("errors.invalid_field", 400, {"field": "leave_type", "allowed": list(TIPOS_DE_AUSENCIA)})
        desde = _fecha(datos.get("start_date"), "start_date")
        hasta = _fecha(datos.get("end_date"), "end_date")
        if hasta < desde:
            raise AppError("errors.invalid_field", 400, {"field": "end_date"})
        if len(str(datos.get("notes") or "")) > 300:
            raise AppError("errors.invalid_field", 400, {"field": "notes"})
        with transaction_context() as db:
            empleado = db.get(User, id_user)
            if empleado is None or empleado.deletion_date is not None or not empleado.is_employee:
                raise AppError("errors.invalid_field", 400, {"field": "id_user", "reason": "not_employee"})
            _exigir_fuera_de_periodo_cerrado(db, desde, hasta)
            for otra in db.scalars(select(EmployeeLeave)
                                   .where(EmployeeLeave.id_user == id_user)
                                   .where(EmployeeLeave.deletion_date.is_(None))
                                   .where(EmployeeLeave.start_date <= hasta)
                                   .where(EmployeeLeave.end_date >= desde)):
                if excluir_id is None or str(otra.id_employee_leave) != str(excluir_id):
                    raise AppError("errors.employee_leave_overlap", 409, {
                        "id_employee_leave": otra.id_employee_leave, "leave_type": otra.leave_type,
                        "start_date": otra.start_date.isoformat(), "end_date": otra.end_date.isoformat()})
            if tipo == VACACIONES:
                cls._validar_vacaciones(db, empleado, desde, hasta, excluir_id)

    @staticmethod
    def _validar_vacaciones(db, empleado: User, desde: date, hasta: date, excluir_id) -> None:
        if not empleado.hire_date:
            raise AppError("errors.employee_leave_no_hire_date", 409, {"id_user": empleado.id_user})
        anios, _, fin = ano_de_servicio(empleado.hire_date, desde)
        if empleado.hire_date > desde or anios < 1:
            raise AppError("errors.employee_leave_first_year", 409, {
                "first_anniversary": _aniversario(empleado.hire_date, 1).isoformat()})
        if hasta > fin:
            raise AppError("errors.employee_leave_crosses_anniversary", 409, {
                "anniversary": (fin + timedelta(days=1)).isoformat()})
        pedidos, con_horario = dias_laborables(db, empleado.id_user, desde, hasta)
        if not con_horario:
            raise AppError("errors.employee_leave_needs_schedule", 409, {"id_user": empleado.id_user})
        if pedidos == 0:
            raise AppError("errors.employee_leave_no_workdays", 400, {"field": "start_date"})
        saldo = saldo_de_vacaciones(db, empleado, desde, excluir_id)
        if pedidos > saldo["available"]:
            raise AppError("errors.employee_leave_insufficient_balance", 409, {
                "available": saldo["available"], "requested": pedidos, "entitled": saldo["entitled"]})

    @classmethod
    def _actual(cls, item_id) -> dict:
        actual = cls.get(item_id)
        if actual is None:
            raise AppError("errors.resource_not_found", 404)
        return actual

    @classmethod
    def create(cls, payload: dict, user_id: int | None = None):
        cls._validar(dict(payload or {}))
        return super().create(payload, user_id=user_id)

    @classmethod
    def update(cls, item_id, payload: dict, user_id: int | None = None):
        actual = cls._actual(item_id)
        with transaction_context() as db:
            _exigir_fuera_de_periodo_cerrado(db, _fecha(actual["start_date"], "start_date"),
                                             _fecha(actual["end_date"], "end_date"))
        cls._validar({**actual, **dict(payload or {})}, excluir_id=item_id)
        return super().update(item_id, payload, user_id=user_id)

    @classmethod
    def delete(cls, item_id, user_id: int | None = None):
        actual = cls._actual(item_id)
        with transaction_context() as db:
            _exigir_fuera_de_periodo_cerrado(db, _fecha(actual["start_date"], "start_date"),
                                             _fecha(actual["end_date"], "end_date"))
        return super().delete(item_id, user_id=user_id)
