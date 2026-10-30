"""El numero de lecturas del calculo, el resumen y el saldo no crece con los empleados.

Antes de la optimizacion (2026-10-22) eran unas 14 consultas por empleado en el
calculo, 1 por empleado en el resumen y varias por ausencia en el saldo de
vacaciones. Aqui se cuentan con 1 y con 5 empleados mas: deben ser las mismas.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import event

from app.models import AttendanceRecord, EmployeeLeave, User
from app.models.session import engine, transaction_context
from app.services.employee_leave_service import saldos
from app.services.payroll_calculation_service import calcular_periodo, resumen_periodo
from tests.test_services.test_payroll_calculation_service import _ConPeriodoDePrueba


@contextmanager
def _contar():
    cuenta = {"n": 0}

    def sumar(_conn, _cursor, sentencia, *_args, **_kw):
        # Solo lecturas: guardar un renglon por empleado es inevitable, y en
        # SQLite (la base de las pruebas) cada escritura se cuenta aparte.
        if sentencia.lstrip().upper().startswith("SELECT"):
            cuenta["n"] += 1

    event.listen(engine, "before_cursor_execute", sumar)
    try:
        yield cuenta
    finally:
        event.remove(engine, "before_cursor_execute", sumar)


class TestConsultasNoCrecenConLosEmpleados(_ConPeriodoDePrueba):

    def _agregar_empleados(self, cuantos, desde_id=200):
        with transaction_context() as db:
            for i in range(cuantos):
                id_user = desde_id + i
                db.add(User(id_user=id_user, created_by=1, full_name=f"Extra {i}", id_permission=1, id_proyect=1,
                            id_status=1, supervisor=1, user_type="employee", is_employee=True,
                            base_salary=Decimal("400.00"), hire_date=date(2020, 1, 15), username=f"x{id_user}"))
                db.add(AttendanceRecord(id_user=id_user, employee_no=str(id_user), check_time=datetime(2026, 10, 2, 9, 0),
                                        source="kronos", source_ref=f"x:{id_user}", created_by=1))
                db.add(EmployeeLeave(id_user=id_user, leave_type="vacation", start_date=date(2026, 3, 2),
                                     end_date=date(2026, 3, 3), created_by=1))

    def _consultas(self):
        calcular_periodo(5, 1)   # la primera vez crea conceptos y detalles; se mide un recalculo
        with _contar() as calculo:
            calcular_periodo(5, 1)
        with _contar() as resumen:
            resumen_periodo(5)
        with _contar() as saldo:
            saldos()
        return calculo["n"], resumen["n"], saldo["n"]

    def test_las_mismas_consultas_con_mas_empleados(self):
        self._agregar_empleados(1)
        con_pocos = self._consultas()
        self._agregar_empleados(5, desde_id=300)
        con_mas = self._consultas()
        self.assertEqual(con_pocos, con_mas)
