"""Politica de vacaciones de la empresa (revision contable, 2026-10-28).

Ana (71): salario 500, horario L-V desde el 1 de octubre de 2026, ingreso el
1 de marzo de 2024; su jefe es Beto (80). Aniversarios: 2025-03-01, 2026-03-01 y
2027-03-01. Al 20 de octubre de 2026 va en su 3er año: por ley tiene el bloque
de su 2o año, 14 dias, que vence en su siguiente aniversario (2027-03-01).

Cuentas a mano:
  Mes a mes: el bloque del 2o año (14) ya completo y vigente hasta 2027-03-01, mas
    el del 3er año (16 dias) por los 7 meses completos desde 2026-03-01:
    16 x 7 // 12 = 9. Ganados: 14 + 9 = 23.
  Plazo de 18 meses: el bloque del 2o año vence el 2027-09-01. Al 1 de abril de
    2027 sigue vigente junto con el del 3er año (16): 30.
  Pago al vencer: con ingreso el 10 de octubre de 2024, el bloque del 1er año
    (12 dias) vence el 10 de octubre de 2026, dentro del periodo 5 (1 al 15):
    12 x 500 = 6,000.00, grava como sueldo. El mismo dia cumple 2 años: prima de
    14 x 500 x 25 % = 1,750.00, exenta (tope 15 UMA = 1,759.65). Base gravable:
    3,500 de sueldo (7 dias pagados) + 6,000 = 9,500.00.
"""
from __future__ import annotations

from datetime import date

from app.models import Notification, PayrollParameter, User
from app.models.session import transaction_context
from app.services.employee_leave_service import (EmployeeLeaveService, avisar_vacaciones_por_vencer,
                                                 saldo_de_vacaciones)
from app.services.payroll_calculation_service import calcular_periodo
from app.services.payroll_parameter_service import PayrollParameterService
from app.utils.errors import AppError
from tests.test_services.test_solicitudes_de_vacaciones import ANA, _ConEquipo


class _ConPolitica(_ConEquipo):
    def politica(self, clave, valor):
        with transaction_context() as db:
            db.add(PayrollParameter(parameter_key=clave, value=valor, valid_from=date(2026, 1, 1),
                                    source="Prueba", created_by=1))

    def saldo(self, al_dia=date(2026, 10, 20)):
        with transaction_context() as db:
            return saldo_de_vacaciones(db, db.get(User, ANA), al_dia)

    def vacaciones(self, desde, hasta):
        return EmployeeLeaveService.create({"id_user": ANA, "leave_type": "vacation", "start_date": desde,
                                            "end_date": hasta}, user_id=1)

    def error(self, desde, hasta):
        with self.assertRaises(AppError) as error:
            self.vacaciones(desde, hasta)
        return error.exception.message_key


class TestComoSeGanan(_ConPolitica):
    def test_por_omision_el_bloque_completo_al_aniversario(self):
        s = self.saldo()
        self.assertEqual((14, 14, 0, False), (s["entitled"], s["available"], s["advanced"], s["monthly_accrual"]))
        self.assertEqual([{"service_year": 2, "days": 14, "expires_on": "2027-03-01"}], s["expiring"])

    def test_mes_a_mes_suma_lo_ganado_del_ano_en_curso(self):
        self.politica("vacation_accrual_monthly", 1)
        s = self.saldo()
        self.assertEqual((23, 23, True), (s["entitled"], s["available"], s["monthly_accrual"]))

    def test_mes_a_mes_ya_hay_vacaciones_el_primer_ano(self):
        with transaction_context() as db:
            db.get(User, ANA).hire_date = date(2026, 3, 1)
        self.assertEqual("errors.employee_leave_first_year", self.error("2026-10-05", "2026-10-09"))
        self.politica("vacation_accrual_monthly", 1)
        self.vacaciones("2026-10-05", "2026-10-09")    # 7 meses completos: 12 x 7 // 12 = 7 ganados
        self.assertEqual((7, 2), (self.saldo()["entitled"], self.saldo()["available"]))


class TestAdelantar(_ConPolitica):
    def test_sin_adelanto_no_pasa_del_saldo(self):
        self.assertEqual("errors.employee_leave_insufficient_balance", self.error("2026-10-01", "2026-10-23"))

    def test_con_adelanto_toma_hasta_el_maximo(self):
        self.politica("vacation_advance_max_days", 3)
        self.vacaciones("2026-10-01", "2026-10-23")    # 17 laborables: 14 del saldo + 3 adelantados
        s = self.saldo()
        self.assertEqual((0, 3, 0), (s["available"], s["advanced"], s["can_advance"]))
        self.assertEqual("errors.employee_leave_insufficient_balance", self.error("2026-10-26", "2026-10-26"))


class TestPlazoYNoUsados(_ConPolitica):
    def test_con_18_meses_el_bloque_anterior_sigue_vigente(self):
        self.assertEqual(16, self.saldo(date(2027, 4, 1))["entitled"])
        self.politica("vacation_expiry_months", 18)
        s = self.saldo(date(2027, 4, 1))
        self.assertEqual(30, s["entitled"])
        self.assertIn({"service_year": 2, "days": 14, "expires_on": "2027-09-01"}, s["expiring"])

    def test_si_se_acumulan_no_vencen(self):
        self.politica("vacation_unused_policy", 1)
        s = self.saldo(date(2027, 4, 1))
        # Nunca uso ninguno: los del 1er, 2o y 3er año siguen ahi (12 + 14 + 16).
        self.assertEqual((42, []), (s["entitled"], s["expiring"]))

    def test_si_se_pagan_entran_a_la_nomina_del_periodo_en_que_vencen(self):
        with transaction_context() as db:
            db.get(User, ANA).hire_date = date(2024, 10, 10)
        ana = next(e for e in calcular_periodo(5, 1)["employees"] if e["id_user"] == ANA)
        self.assertEqual((0, 0.0), (ana["unused_vacation_days_paid"], ana["unused_vacation_pay"]))
        self.politica("vacation_unused_policy", 2)
        ana = next(e for e in calcular_periodo(5, 1)["employees"] if e["id_user"] == ANA)
        self.assertEqual((12, 6000.0), (ana["unused_vacation_days_paid"], ana["unused_vacation_pay"]))
        self.assertEqual((1750.0, 0.0), (ana["vacation_premium"], ana["vacation_premium_taxable"]))
        self.assertEqual(9500.0, ana["taxable_income"])


class TestAvisos(_ConPolitica):
    def _avisos(self):
        with transaction_context() as db:
            return sorted(n.id_user_recipient for n in db.query(Notification)
                          .filter_by(notification_type="vacation_expiring"))

    def test_avisa_al_empleado_y_a_su_jefe_60_y_30_dias_antes(self):
        self.assertEqual(0, avisar_vacaciones_por_vencer(date(2026, 12, 30)))
        self.assertEqual(2, avisar_vacaciones_por_vencer(date(2026, 12, 31)))   # 60 dias antes del 2027-03-01
        self.assertEqual(2, avisar_vacaciones_por_vencer(date(2027, 1, 30)))    # 30 dias antes
        self.assertEqual([ANA, ANA, 80, 80], self._avisos())

    def test_sin_avisos_si_se_acumulan(self):
        self.politica("vacation_unused_policy", 1)
        self.assertEqual(0, avisar_vacaciones_por_vencer(date(2026, 12, 31)))


class TestValidaciones(_ConPolitica):
    def test_solo_valores_que_el_saldo_sabe_usar(self):
        for clave, valor in (("vacation_expiry_months", 15), ("vacation_unused_policy", 3),
                             ("vacation_advance_max_days", 61), ("vacation_accrual_monthly", 2),
                             ("vacation_warning_days_1", 1.5)):
            with self.assertRaises(AppError, msg=clave):
                PayrollParameterService.create({"parameter_key": clave, "value": valor, "valid_from": "2027-01-01"},
                                               user_id=1)
        creado = PayrollParameterService.create({"parameter_key": "vacation_expiry_months", "value": 18,
                                                 "valid_from": "2027-01-01"}, user_id=1)
        self.assertEqual(18, creado["value"])
