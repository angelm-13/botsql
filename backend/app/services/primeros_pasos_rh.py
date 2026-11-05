"""Primeros pasos de RH (revision de usabilidad de Angel, 2026-11-05).

Quien entra a RH por primera vez no sabe por donde empezar. Esta lista dice, con
los datos reales, cuantos de los 9 pasos de la puesta en marcha ya estan listos y
lleva a la pantalla de cada uno. Solo lectura: no cambia ninguna regla.
"""
from __future__ import annotations

from sqlalchemy import func, or_, select

from app.models import (AttendanceEmployeeLink, EmployeeLeave, EmployeePayrollGroup, EmployeeSchedule, PayrollGroup,
                        PayrollIsrBracket, PayrollPeriod, User, WorkSchedule)
from app.models.employee_leave import ESTADOS_PENDIENTES
from app.models.session import transaction_context
from app.utils.tiempo import ahora_negocio


def _vigente(modelo, hoy):
    return ((modelo.valid_from <= hoy) & or_(modelo.valid_to.is_(None), modelo.valid_to >= hoy)
            & modelo.deletion_date.is_(None))


def pasos(hoy=None) -> dict:
    from app.services import salary_service as salarios
    from app.services.payroll_calculation_service import _vigentes
    hoy = hoy or ahora_negocio().date()
    with transaction_context() as db:
        cifras = _vigentes(db, ("uma_daily", "minimum_wage_daily"), hoy)
        tarifa = db.scalar(select(func.count(PayrollIsrBracket.id_payroll_isr_bracket))
                           .where(PayrollIsrBracket.valid_year == hoy.year)
                           .where(PayrollIsrBracket.deletion_date.is_(None))) or 0
        horarios = db.scalar(select(func.count(WorkSchedule.id_work_schedule))
                             .where(WorkSchedule.deletion_date.is_(None))) or 0
        por_omision = db.scalar(select(func.count(PayrollGroup.id_payroll_group))
                                .where(PayrollGroup.is_default.is_(True))
                                .where(PayrollGroup.deletion_date.is_(None))) or 0
        empleados = list(db.scalars(select(User).where(User.is_employee.is_(True))
                                    .where(User.deletion_date.is_(None))))
        ids = [e.id_user for e in empleados]
        con_horario = set(db.scalars(select(EmployeeSchedule.id_user).where(EmployeeSchedule.id_user.in_(ids or [0]))
                                     .where(_vigente(EmployeeSchedule, hoy))))
        con_grupo = set(db.scalars(select(EmployeePayrollGroup.id_user)
                                   .where(EmployeePayrollGroup.id_user.in_(ids or [0]))
                                   .where(_vigente(EmployeePayrollGroup, hoy))))
        sueldos = salarios.sueldos_vigentes(db, ids, hoy) if ids else {}
        # Sin grupo propio cobra en el de por omision; sin forma de salario, con su salario base de respaldo.
        sin_datos = [e for e in empleados if e.id_user not in con_horario
                     or (e.id_user not in con_grupo and not por_omision)
                     or (e.id_user not in sueldos and not e.base_salary)]
        ligados = set(db.scalars(select(AttendanceEmployeeLink.id_user).where(AttendanceEmployeeLink.id_user.in_(ids or [0]))
                                 .where(AttendanceEmployeeLink.deletion_date.is_(None))))
        sin_reloj = [e for e in empleados if e.id_user not in ligados]
        pendientes = db.scalar(select(func.count(EmployeeLeave.id_employee_leave))
                               .where(EmployeeLeave.leave_status.in_(ESTADOS_PENDIENTES))
                               .where(EmployeeLeave.deletion_date.is_(None))) or 0
        estados = {s for s in db.scalars(select(PayrollPeriod.period_state).where(PayrollPeriod.deletion_date.is_(None)))}
    lista = [
        {"key": "figures", "path": "/payroll_settings", "done": "uma_daily" in cifras and "minimum_wage_daily" in cifras and tarifa > 0},
        {"key": "schedules", "path": "/work_schedules", "done": horarios > 0, "count": horarios},
        {"key": "groups", "path": "/payroll_groups", "done": por_omision > 0},
        {"key": "employees", "path": "/user", "done": bool(empleados), "count": len(empleados)},
        {"key": "payroll_data", "path": "/user", "done": bool(empleados) and not sin_datos, "count": len(sin_datos),
         "names": [e.full_name or e.username for e in sin_datos[:5]]},
        {"key": "attendance", "path": "/kronos", "done": bool(empleados) and not sin_reloj, "count": len(sin_reloj),
         "names": [e.full_name or e.username for e in sin_reloj[:5]]},
        {"key": "leaves", "path": "/employee_leaves", "done": pendientes == 0, "count": pendientes},
        {"key": "calculated", "path": "/payroll_period", "done": bool(estados & {"calculated", "closed"})},
        {"key": "closed", "path": "/payroll_period", "done": "closed" in estados},
    ]
    return {"steps": lista, "done": sum(1 for p in lista if p["done"]), "total": len(lista)}
