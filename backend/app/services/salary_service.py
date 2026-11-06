"""Formas de salario por empleado (decisiones de RH, 2026-10-30).

Cada empleado gana de una forma, segun su contrato, con vigencia:

* Por dia (como siempre): sueldo del periodo = diario x dias pagados.
* Por hora: cada dia trabajado se paga de su primera a su ultima checada, SIN
  quitar la comida (se paga), con tope en la duracion de su horario ese dia;
  lo que pase de ahi es hora extra y necesita autorizacion
  (overtime_service). Los dias pagados sin trabajo -descanso, festivo,
  vacaciones, permiso con goce- se pagan con su diario equivalente.
* Fijo por periodo (semana, catorcena, quincena o mes): si el periodo es de esa
  misma periodicidad se paga el monto, menos el monto llevado a dia por cada
  dia no pagado (faltas, permiso sin goce, incapacidad); si no, diario x dias
  pagados.

Diario equivalente (lo que usan IMSS, aguinaldo, prima vacacional y vacaciones,
que la ley cuenta por dia): por dia = el monto; por hora = el monto x las horas
de su horario (comida incluida; sin horario, `overtime_day_hours`); fijo = el
monto / 7, 14, 15 o 30.

Quien no tiene forma capturada sigue con `user.base_salary` como diario.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import select

from app.models import EmployeeSalary, User
from app.models.employee_salary import DIAS_DEL_FIJO, FIJO, FORMAS, POR_DIA, POR_HORA
from app.models.session import transaction_context
from app.services import payroll_tax_rules as ley
from app.services.base_service import CrudService
from app.services.work_schedule_service import _entero, _fecha
from app.utils.errors import AppError


class EmployeeSalaryService(CrudService):
    """Forma de salario de un empleado; las vigencias de una persona no se enciman."""

    model = EmployeeSalary
    primary_key = 'id_employee_salary'
    entity_name = 'employee_salary'

    @classmethod
    def _validar(cls, datos: dict, excluir_id=None) -> dict:
        id_user = _entero(datos.get("id_user"), "id_user")
        forma = datos.get("salary_type")
        if forma not in FORMAS:
            raise AppError("errors.invalid_field", 400, {"field": "salary_type", "allowed": list(FORMAS)})
        try:
            monto = Decimal(str(datos.get("amount")))
        except Exception as exc:
            raise AppError("errors.invalid_field", 400, {"field": "amount"}) from exc
        if not monto > 0:
            raise AppError("errors.invalid_field", 400, {"field": "amount"})
        frecuencia = datos.get("fixed_frequency") or None
        if forma == FIJO and frecuencia not in DIAS_DEL_FIJO:
            raise AppError("errors.invalid_field", 400, {"field": "fixed_frequency", "allowed": list(DIAS_DEL_FIJO)})
        desde = _fecha(datos.get("valid_from"), "valid_from")
        hasta = _fecha(datos.get("valid_to"), "valid_to", opcional=True)
        if hasta is not None and hasta < desde:
            raise AppError("errors.invalid_field", 400, {"field": "valid_to"})
        with transaction_context() as db:
            empleado = db.get(User, id_user)
            if empleado is None or empleado.deletion_date is not None or not empleado.is_employee:
                raise AppError("errors.invalid_field", 400, {"field": "id_user", "reason": "not_employee"})
            for otro in db.scalars(select(EmployeeSalary).where(EmployeeSalary.id_user == id_user)
                                   .where(EmployeeSalary.deletion_date.is_(None))):
                if excluir_id is not None and str(otro.id_employee_salary) == str(excluir_id):
                    continue
                if desde <= (otro.valid_to or date.max) and otro.valid_from <= (hasta or date.max):
                    raise AppError("errors.employee_salary_overlap", 409, {
                        "id_employee_salary": otro.id_employee_salary, "valid_from": otro.valid_from.isoformat(),
                        "valid_to": otro.valid_to.isoformat() if otro.valid_to else None})
        # La periodicidad solo la lleva un sueldo fijo.
        return {"fixed_frequency": frecuencia if forma == FIJO else None}

    @classmethod
    def create(cls, payload: dict, user_id: int | None = None):
        payload = dict(payload or {})
        payload.update(cls._validar(payload))
        return super().create(payload, user_id=user_id)

    @classmethod
    def update(cls, item_id, payload: dict, user_id: int | None = None):
        payload = dict(payload or {})
        payload.update(cls._validar({**cls.get(item_id), **payload}, excluir_id=item_id))
        return super().update(item_id, payload, user_id=user_id)


# ------------------------------------------------------------------ reglas que usa el calculo

def sueldos_vigentes(db, ids, al_dia: date) -> dict:
    """{id_user: EmployeeSalary} vigente `al_dia`."""
    return {s.id_user: s for s in db.scalars(
        select(EmployeeSalary).where(EmployeeSalary.id_user.in_(list(ids) or [0]))
        .where(EmployeeSalary.deletion_date.is_(None))
        .where(EmployeeSalary.valid_from <= al_dia)
        .where((EmployeeSalary.valid_to.is_(None)) | (EmployeeSalary.valid_to >= al_dia)))}


def _minutos_del_horario(dia) -> int | None:
    if dia.entrada is None or dia.salida is None:
        return None
    return int((datetime.combine(dia.fecha, dia.salida) - datetime.combine(dia.fecha, dia.entrada)).total_seconds() // 60)


def diario_equivalente(sueldo, dias, horas_sin_horario: int) -> Decimal:
    """El salario diario que vale para IMSS, aguinaldo, prima y vacaciones."""
    monto = Decimal(str(sueldo.amount))
    if sueldo.salary_type == POR_DIA:
        return ley.dinero(monto)
    if sueldo.salary_type == FIJO:
        return ley.dinero(monto / DIAS_DEL_FIJO[sueldo.fixed_frequency])
    # Por hora: las horas de su horario (el primer dia laboral del periodo), comida incluida.
    minutos = next((m for m in (_minutos_del_horario(d) for d in dias if d.laboral) if m), horas_sin_horario * 60)
    return ley.dinero(monto * minutos / 60)


def sueldo_del_periodo(sueldo, diario: Decimal, dias, frecuencia_del_periodo: str | None) -> Decimal:
    """Lo que se le paga de sueldo en el periodo, segun su forma. `dias`: los Dia del periodo."""
    pagados = sum(d.pagado for d in dias)
    if sueldo is None or sueldo.salary_type == POR_DIA:
        return ley.dinero(diario * pagados)
    if sueldo.salary_type == FIJO:
        if sueldo.fixed_frequency == frecuencia_del_periodo:
            return ley.dinero(max(Decimal(str(sueldo.amount)) - diario * (len(dias) - pagados), Decimal(0)))
        return ley.dinero(diario * pagados)
    tarifa = Decimal(str(sueldo.amount))
    total = Decimal(0)
    for d in dias:
        if not d.pagado:
            continue
        if d.laboral and len(d.marcas) >= 2 and d.ausencia is None:
            trabajado = int((datetime.combine(d.fecha, d.marcas[-1]) - datetime.combine(d.fecha, d.marcas[0]))
                            .total_seconds() // 60)
            tope = _minutos_del_horario(d) or trabajado
            total += tarifa * min(trabajado, tope) / 60
        elif not d.con_horario and len(d.marcas) >= 2:
            trabajado = int((datetime.combine(d.fecha, d.marcas[-1]) - datetime.combine(d.fecha, d.marcas[0]))
                            .total_seconds() // 60)
            total += tarifa * min(trabajado, diario / tarifa * 60) / 60
        else:
            total += diario   # descanso, festivo, vacaciones, permiso con goce
    return ley.dinero(total)


def precio_de_hora(sueldo) -> Decimal | None:
    """La hora de quien gana por hora (para sus horas extra); None = se saca del diario."""
    return Decimal(str(sueldo.amount)) if sueldo is not None and sueldo.salary_type == POR_HORA else None
