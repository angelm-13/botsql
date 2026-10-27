"""Opciones de calculo de cada empresa y su tabla de vacaciones (revision contable, 2026-10-26).

Ana, como en test_employee_leave: salario diario 500, horario L-V desde el 1 de
octubre, checadas los dias 1, 2 y 5, ingreso el 1 de marzo de 2024 (2 años
cumplidos, va en su 3er año). Periodo 5 = 1 al 15 de octubre de 2026: 7 dias
pagados y 8 faltas (6, 7, 8, 9, 12, 13, 14 y 15).

Cuentas a mano:
  Factor con 16 dias de vacaciones: 1 + (15 + 16 x 25 %) / 365 = 1.0521
  SBC 500 x 1.0521 = 526.05; cuota por dia 526.05 x 2.375 % + (526.05 - 351.93) x 0.40 % = 13.1902
  IMSS: 7 dias = 92.33; 15 dias (cotizando las 8 faltas) = 197.85
  Subsidio con 30.4: 3,566.22 x 15.02 % / 30.4 x 15 = 264.30; con los 31 dias de octubre: 259.18
"""
from __future__ import annotations

import unittest
from datetime import date
from decimal import Decimal

from app.models import EmployeeLeave, PayrollParameter, PayrollPeriod, User
from app.models.session import transaction_context
from app.services import payroll_tax_rules as ley
from app.services.employee_leave_service import EmployeeLeaveService, saldo_de_vacaciones
from app.services.payroll_calculation_service import calcular_periodo
from app.services.payroll_parameter_service import PayrollParameterService
from app.utils.errors import AppError
from tests.test_services.test_employee_leave import _ConAusencias


class TestReglas(unittest.TestCase):
    """Reglas sueltas, sin base de datos."""

    def test_subsidio_con_los_dias_reales_del_mes(self):
        self.assertEqual(Decimal("264.30"), ley.subsidio_para_el_empleo(5000, 15, "3566.22", "15.02", "11492.66"))
        self.assertEqual(Decimal("259.18"), ley.subsidio_para_el_empleo(5000, 15, "3566.22", "15.02", "11492.66", 31))
        # Febrero: 535.6462 / 28 x 15
        self.assertEqual(Decimal("286.95"), ley.subsidio_para_el_empleo(5000, 15, "3566.22", "15.02", "11492.66", 28))

    def test_la_tabla_de_la_empresa_nunca_da_menos_que_la_ley(self):
        tabla = {1: 15, 6: 25}
        self.assertEqual(15, ley.dias_de_vacaciones(0, tabla))    # año 1: 15 > 12 de ley
        self.assertEqual(20, ley.dias_de_vacaciones(4, tabla))    # año 5: el renglon del año 1 da 15, la ley 20
        self.assertEqual(25, ley.dias_de_vacaciones(5, tabla))    # año 6: 25 > 22
        self.assertEqual(25, ley.dias_de_vacaciones(10, tabla))   # año 11: sigue el renglon del año 6
        self.assertEqual(12, ley.dias_de_vacaciones(0, {1: 5}))   # capturar menos no baja de la ley
        self.assertEqual(12, ley.dias_de_vacaciones(0, None))

    def test_el_aguinaldo_descuenta_los_dias_indicados(self):
        # 450 x 15 x (365 - 10) / 365
        self.assertEqual(Decimal("6565.07"), ley.aguinaldo(450, 15, date(2020, 3, 1), 2026, 10))
        self.assertEqual(Decimal("6750.00"), ley.aguinaldo(450, 15, date(2020, 3, 1), 2026))


class _ConOpciones(_ConAusencias):
    def _opcion(self, clave, valor):
        with transaction_context() as db:
            db.add(PayrollParameter(parameter_key=clave, value=valor, valid_from=date(2026, 1, 1),
                                    source="Prueba", created_by=1))

    def _ana(self):
        return calcular_periodo(5, 1)["employees"][0]


class TestImssEnFaltas(_ConOpciones):
    def test_por_omision_solo_cotizan_los_dias_pagados(self):
        ana = self._ana()
        self.assertEqual((7, 8, 7), (ana["days_worked"], ana["absences"], ana["imss_days"]))
        self.assertEqual(1.0521, ana["integration_factor"])
        self.assertEqual(92.33, ana["imss"])

    def test_con_la_opcion_las_faltas_tambien_cotizan(self):
        self._opcion("option_imss_on_absences", 1)
        ana = self._ana()
        self.assertEqual((7, 15), (ana["days_worked"], ana["imss_days"]))
        self.assertEqual(197.85, ana["imss"])
        self.assertEqual(3500.0, ana["salary"])   # el sueldo no cambia: solo la cuota


class TestAguinaldoConDescuentos(_ConOpciones):
    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.get(PayrollPeriod, 5).includes_aguinaldo = True
        # Incapacidad general el 6 y 7 (2 dias naturales) y de maternidad el 8: esos
        # dias dejan de ser falta. Quedan 5 faltas: 9, 12, 13, 14 y 15.
        for desde, hasta, tipo in (("2026-10-06", "2026-10-07", "general_illness"),
                                   ("2026-10-08", "2026-10-08", "maternity")):
            EmployeeLeaveService.create({"id_user": 71, "leave_type": "disability", "start_date": desde,
                                         "end_date": hasta, "disability_type": tipo}, user_id=1)

    def test_por_omision_el_aguinaldo_va_completo(self):
        ana = self._ana()
        self.assertEqual((0, 7500.0), (ana["aguinaldo_discounted_days"], ana["aguinaldo"]))

    def test_con_la_opcion_bajan_las_faltas_y_la_incapacidad_general(self):
        self._opcion("option_aguinaldo_discounts", 1)
        ana = self._ana()
        # 5 faltas + 2 dias de incapacidad general; la de maternidad no cuenta.
        self.assertEqual(7, ana["aguinaldo_discounted_days"])
        self.assertEqual(7356.16, ana["aguinaldo"])   # 500 x 15 x 358 / 365

    def test_sin_tipo_capturado_la_incapacidad_no_se_descuenta(self):
        with transaction_context() as db:
            for a in db.query(EmployeeLeave).filter(EmployeeLeave.disability_type == "general_illness"):
                a.disability_type = None
        self._opcion("option_aguinaldo_discounts", 1)
        self.assertEqual(5, self._ana()["aguinaldo_discounted_days"])


class TestSubsidioConDiasDelMes(_ConOpciones):
    def test_octubre_usa_31_dias_con_la_opcion(self):
        self.assertEqual(264.30, self._ana()["employment_subsidy"])
        self._opcion("option_subsidy_month_days", 1)
        self.assertEqual(259.18, self._ana()["employment_subsidy"])


class TestTablaDeVacacionesDeLaEmpresa(_ConOpciones):
    def _saldo(self):
        with transaction_context() as db:
            return saldo_de_vacaciones(db, db.get(User, 71), date(2026, 10, 20))

    def test_el_saldo_y_el_factor_usan_la_tabla(self):
        self._opcion("vacation_days_year_2", 18)   # el año que cumplio: le tocan 18 y no 14
        self._opcion("vacation_days_year_3", 20)   # su año en curso: el factor usa 20 y no 16
        self.assertEqual(18, self._saldo()["entitled"])
        self.assertEqual(1.0548, self._ana()["integration_factor"])   # 1 + (15 + 20 x 25 %) / 365

    def test_capturar_menos_que_la_ley_no_baja_el_saldo(self):
        self._opcion("vacation_days_year_2", 5)
        self.assertEqual(14, self._saldo()["entitled"])


class TestValidaciones(_ConOpciones):
    def _crear(self, clave, valor):
        return PayrollParameterService.create({"parameter_key": clave, "value": valor, "valid_from": "2027-01-01"},
                                              user_id=1)

    def _error(self, clave, valor):
        with self.assertRaises(AppError) as error:
            self._crear(clave, valor)
        return error.exception

    def test_una_opcion_solo_es_si_o_no(self):
        self.assertEqual("errors.invalid_field", self._error("option_imss_on_absences", 2).message_key)
        self.assertEqual(1, self._crear("option_imss_on_absences", 1)["value"])

    def test_los_dias_de_vacaciones_son_enteros(self):
        self.assertEqual("whole_days", self._error("vacation_days_year_1", "12.5").meta["reason"])
        self.assertEqual("whole_days", self._error("vacation_days_year_1", 0).meta["reason"])
        self.assertEqual(15, self._crear("vacation_days_year_1", 15)["value"])

    def test_una_clave_desconocida_no_entra(self):
        self.assertEqual("parameter_key", self._error("option_inventada", 1).meta["field"])

    def test_el_tipo_de_incapacidad(self):
        error = None
        try:
            EmployeeLeaveService.create({"id_user": 71, "leave_type": "disability", "start_date": "2026-10-20",
                                         "end_date": "2026-10-20", "disability_type": "gripa"}, user_id=1)
        except AppError as e:
            error = e
        self.assertEqual("disability_type", error.meta["field"])
        # En otro tipo de ausencia el tipo de incapacidad no se guarda.
        permiso = EmployeeLeaveService.create({"id_user": 71, "leave_type": "paid_leave", "start_date": "2026-10-21",
                                               "end_date": "2026-10-21", "disability_type": "maternity"}, user_id=1)
        self.assertIsNone(permiso["disability_type"])
