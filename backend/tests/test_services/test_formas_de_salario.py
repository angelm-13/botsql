"""Formas de salario por empleado (decisiones de RH, 2026-10-30).

Mismo equipo que test_solicitudes_de_vacaciones: Ana (71) trabaja L-V de 9 a 18
(9 horas con la comida, que se paga) y checa de 8:00 a 17:00 los dias 1, 2, 5 y
20 de octubre. Periodo 5 = 1 al 15: 7 dias pagados (los 3 que checo y 4 de fin de
semana) y 8 faltas.

Cuentas a mano:
  Por hora a $65: cada dia trabajado 9 h (de 8:00 a 17:00, tope 9 h de su horario)
  = $585 x 3 = $1,755; los 4 dias de descanso con su diario equivalente
  ($65 x 9 h = $585) = $2,340. Sueldo: $4,095.00.
  Fijo de $9,000 la quincena (diario $600) en la quincena del 16 al 31 (16 dias,
  10 faltas, 6 pagados): 9,000 - 600 x 10 = $3,000.00. Por dia seria 600 x 6 = $3,600.
  Hora extra de quien gana por hora: 1 h doble = $65 x 2 = $130.00.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from app.models import AttendanceRecord, EmployeeSalary, PayrollGroup, PayrollPeriod
from app.models.session import transaction_context
from app.services.overtime_service import registrar
from app.services.payroll_calculation_service import calcular_periodo
from app.services.salary_service import EmployeeSalaryService
from app.utils.errors import AppError
from tests.test_services.test_solicitudes_de_vacaciones import ANA, BETO, _ConEquipo


class _ConSueldos(_ConEquipo):
    def sueldo(self, forma, monto, frecuencia=None, desde=date(2026, 1, 1)):
        with transaction_context() as db:
            db.add(EmployeeSalary(id_user=ANA, salary_type=forma, amount=Decimal(monto), fixed_frequency=frecuencia,
                                  valid_from=desde, created_by=1))

    def ana(self, periodo=5):
        return next(e for e in calcular_periodo(periodo, 1)["employees"] if e["id_user"] == ANA)


class TestFormas(_ConSueldos):
    def test_sin_forma_capturada_sigue_el_salario_diario(self):
        ana = self.ana()
        self.assertEqual((500.0, 3500.0, "daily"), (ana["daily_salary"], ana["salary"], ana["salary_type"]))

    def test_por_dia_toma_el_monto_capturado(self):
        self.sueldo("daily", "700")
        self.assertEqual((700.0, 4900.0), (self.ana()["daily_salary"], self.ana()["salary"]))

    def test_por_hora_paga_lo_checado_con_la_comida_y_tope_en_su_horario(self):
        self.sueldo("hourly", "65")
        ana = self.ana()
        self.assertEqual((585.0, 4095.0, "hourly"), (ana["daily_salary"], ana["salary"], ana["salary_type"]))

    def test_fijo_de_la_misma_periodicidad_descuenta_los_dias_no_pagados(self):
        self.sueldo("fixed", "9000", "semimonthly")
        with transaction_context() as db:
            grupo = PayrollGroup(group_name="General", pay_frequency="semimonthly", is_default=True, created_by=1)
            db.add(grupo)
            db.flush()
            db.add(PayrollPeriod(id_payroll_period=6, period_start=date(2026, 10, 16), period_end=date(2026, 10, 31),
                                 payment_date=date(2026, 10, 31), id_status=1, created_by=1,
                                 id_payroll_group=grupo.id_payroll_group))
        ana = self.ana(6)
        self.assertEqual((600.0, 6, 10, 3000.0), (ana["daily_salary"], ana["days_worked"], ana["absences"], ana["salary"]))

    def test_fijo_de_otra_periodicidad_paga_por_dia(self):
        self.sueldo("fixed", "3500", "weekly")       # diario 500
        self.assertEqual((500.0, 3500.0), (self.ana()["daily_salary"], self.ana()["salary"]))

    def test_la_hora_extra_de_quien_gana_por_hora_es_su_tarifa(self):
        self.sueldo("hourly", "65")
        with transaction_context() as db:
            for n, hora in enumerate((9, 19)):
                db.add(AttendanceRecord(id_user=ANA, employee_no="71", check_time=datetime(2026, 10, 6, hora),
                                        source="kronos", source_ref=f"fs:{n}", created_by=1))
        registrar({"id_user": BETO, "id_permission": 2}, {"id_user": ANA, "work_date": "2026-10-06", "minutes": 60})
        self.assertEqual(130.0, self.ana()["overtime_pay"])


class TestValidaciones(_ConSueldos):
    def _crear(self, **datos):
        return EmployeeSalaryService.create({"id_user": ANA, "valid_from": "2026-01-01", **datos}, user_id=1)

    def test_el_fijo_lleva_su_periodicidad_y_los_demas_no(self):
        with self.assertRaises(AppError):
            self._crear(salary_type="fixed", amount=9000)
        self.assertIsNone(self._crear(salary_type="hourly", amount=65, fixed_frequency="weekly")["fixed_frequency"])

    def test_las_vigencias_no_se_enciman_y_el_monto_es_positivo(self):
        with self.assertRaises(AppError):
            self._crear(salary_type="daily", amount=0)
        self._crear(salary_type="daily", amount=500, valid_to="2026-06-30")
        with self.assertRaises(AppError) as error:
            self._crear(salary_type="daily", amount=550, valid_from="2026-06-01")
        self.assertEqual("errors.employee_salary_overlap", error.exception.message_key)
        self._crear(salary_type="daily", amount=550, valid_from="2026-07-01")   # el aumento, desde el dia siguiente
