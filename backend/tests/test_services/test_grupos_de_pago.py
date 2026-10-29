"""Grupos de pago (revision contable, 2026-10-28): cada grupo cobra semanal,
catorcenal, quincenal o mensual, y el periodo de un grupo calcula solo a sus
empleados con la tarifa del ISR de su periodicidad.

Ana (salario diario 500) del calculo de nomina, con 3 dias checados por periodo:
sueldo 1,500.00. Cuentas a mano del ISR antes del subsidio:
  Quincenal (aunque la quincena tenga 13 dias): 7.95 + (1,500 - 416.71) x 6.40 % = 77.28
  La misma quincena de 13 dias sin grupo (tarifa diaria x 13):
      0.53 x 13 + (1,500 - 27.79 x 13) x 6.40 % = 79.77
  Catorcenal (diaria x 14): 0.53 x 14 + (1,500 - 27.79 x 14) x 6.40 % = 78.52

Cruce del 1 de febrero (catorcena del 26 de enero al 8 de febrero, 14 dias
pagados; factor 1.0493 del primer año, SBC 524.65):
  IMSS por dia: 524.65 x 2.375 % + (524.65 - 3 UMA) x 0.40 %
      enero (UMA 113.14): 13.2014 x 6 = 79.21; febrero (UMA 117.31): 13.1513 x 8 = 105.21
      total 184.42 (con la UMA de febrero los 14 dias seria 184.12)
  Subsidio con salario de 350 (4,900 en el periodo, 10,640 al mes, bajo el limite):
      enero: 3,439.46 x 15.59 % / 30.4 x 6 = 105.83; febrero: 3,566.22 x 15.02 % / 30.4 x 8 = 140.96
      total 246.79
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

from app.models import EmployeePayrollGroup, PayrollGroup, PayrollPeriod, User
from app.models.session import transaction_context
from app.services.payroll_calculation_service import calcular_periodo
from app.services.payroll_group_service import (EmployeePayrollGroupService, PayrollGroupService,
                                                siguiente_periodo)
from app.utils.errors import AppError
from tests.test_services.test_payroll_calculation_service import _checada, _ConPeriodoDePrueba


class _ConGrupos(_ConPeriodoDePrueba):
    """General (quincenal, por omision) y Obreros (catorcenal); Pepe (salario 400) es obrero."""

    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            general = PayrollGroup(group_name="General", pay_frequency="semimonthly", is_default=True, created_by=1)
            obreros = PayrollGroup(group_name="Obreros", pay_frequency="biweekly", created_by=1)
            db.add_all([general, obreros])
            db.add(User(id_user=74, created_by=1, full_name="Pepe", id_permission=1, id_proyect=1, id_status=1,
                        supervisor=1, user_type="employee", is_employee=True, base_salary=Decimal("400.00"),
                        username="u74"))
            db.flush()
            self.general, self.obreros = general.id_payroll_group, obreros.id_payroll_group
            db.add(EmployeePayrollGroup(id_user=74, id_payroll_group=self.obreros, valid_from=date(2026, 1, 1),
                                        created_by=1))

    def _periodo(self, id_periodo, inicio, fin, grupo):
        with transaction_context() as db:
            db.add(PayrollPeriod(id_payroll_period=id_periodo, period_start=inicio, period_end=fin, payment_date=fin,
                                 id_status=1, created_by=1, id_payroll_group=grupo))

    def _checa(self, id_user, dias, desde=100):
        with transaction_context() as db:
            for n, dia in enumerate(dias):
                db.add(_checada(id_user, datetime.combine(dia, datetime.min.time()).replace(hour=9), desde + n))

    def _de(self, resultado, id_user):
        return next(e for e in resultado["employees"] if e["id_user"] == id_user)


class TestTarifaPorPeriodicidad(_ConGrupos):
    def setUp(self):
        super().setUp()
        self._checa(71, [date(2026, 2, 16), date(2026, 2, 17), date(2026, 2, 18)])

    def test_la_quincena_de_13_dias_usa_la_tarifa_quincenal(self):
        self._periodo(10, date(2026, 2, 16), date(2026, 2, 28), self.general)
        ana = self._de(calcular_periodo(10, 1), 71)
        self.assertEqual(1500.0, ana["salary"])
        self.assertEqual(77.28, ana["isr_before_subsidy"])

    def test_sin_grupo_la_misma_quincena_sigue_con_la_tarifa_por_dias(self):
        self._periodo(10, date(2026, 2, 16), date(2026, 2, 28), None)
        self.assertEqual(79.77, self._de(calcular_periodo(10, 1), 71)["isr_before_subsidy"])

    def test_la_catorcena_usa_la_diaria_por_14_y_no_la_quincenal(self):
        with transaction_context() as db:
            db.add(EmployeePayrollGroup(id_user=71, id_payroll_group=self.obreros, valid_from=date(2026, 2, 1),
                                        created_by=1))
        self._periodo(10, date(2026, 2, 16), date(2026, 3, 1), self.obreros)
        self.assertEqual(78.52, self._de(calcular_periodo(10, 1), 71)["isr_before_subsidy"])


class TestEmpleadosDelGrupo(_ConGrupos):
    def test_cada_periodo_calcula_solo_a_los_de_su_grupo(self):
        self._periodo(10, date(2026, 10, 1), date(2026, 10, 15), self.general)
        self._periodo(11, date(2026, 10, 1), date(2026, 10, 14), self.obreros)
        general = calcular_periodo(10, 1)
        self.assertEqual([71], [e["id_user"] for e in general["employees"]])
        self.assertEqual([72], [e["id_user"] for e in general["without_salary"]])   # Luis: sin grupo -> General
        self.assertEqual([74], [e["id_user"] for e in calcular_periodo(11, 1)["employees"]])

    def test_un_periodo_sin_grupo_calcula_a_todos_como_antes(self):
        self.assertEqual({71, 74}, {e["id_user"] for e in calcular_periodo(5, 1)["employees"]})

    def test_el_cambio_de_grupo_vale_desde_su_fecha(self):
        EmployeePayrollGroupService.create({"id_user": 71, "id_payroll_group": self.obreros,
                                            "valid_from": "2026-11-01"}, user_id=1)
        self._periodo(10, date(2026, 10, 16), date(2026, 10, 31), self.general)
        self._periodo(11, date(2026, 11, 1), date(2026, 11, 15), self.general)
        self.assertIn(71, [e["id_user"] for e in calcular_periodo(10, 1)["employees"]])
        self.assertNotIn(71, [e["id_user"] for e in calcular_periodo(11, 1)["employees"]])

    def test_el_largo_del_periodo_debe_cuadrar_con_la_periodicidad(self):
        self._periodo(10, date(2026, 10, 1), date(2026, 10, 20), self.general)
        with self.assertRaises(AppError) as error:
            calcular_periodo(10, 1)
        self.assertEqual("errors.payroll_period_length", error.exception.message_key)
        self.assertEqual((13, 16, 20), (error.exception.meta["min_days"], error.exception.meta["max_days"],
                                        error.exception.meta["days"]))


class TestUmaDeCadaDia(_ConGrupos):
    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.add(EmployeePayrollGroup(id_user=71, id_payroll_group=self.obreros, valid_from=date(2026, 1, 1),
                                        created_by=1))
        self._checa(71, [date(2026, 1, 26) + timedelta(days=n) for n in range(14)])
        self._periodo(10, date(2026, 1, 26), date(2026, 2, 8), self.obreros)

    def test_el_imss_usa_la_uma_de_enero_y_la_de_febrero(self):
        ana = self._de(calcular_periodo(10, 1), 71)
        self.assertEqual((14, 14), (ana["days_worked"], ana["imss_days"]))
        self.assertEqual(184.42, ana["imss"])

    def test_el_subsidio_usa_el_porcentaje_y_la_uma_de_cada_mes(self):
        with transaction_context() as db:
            db.get(User, 71).base_salary = Decimal("350.00")
        self.assertEqual(246.79, self._de(calcular_periodo(10, 1), 71)["employment_subsidy"])


class TestSiguientePeriodo(_ConGrupos):
    def test_despues_del_ultimo_periodo_del_grupo(self):
        self._periodo(10, date(2026, 10, 1), date(2026, 10, 15), self.general)
        self._periodo(11, date(2026, 10, 1), date(2026, 10, 14), self.obreros)
        self.assertEqual(("2026-10-16", "2026-10-31"), self._fechas(self.general))
        self.assertEqual(("2026-10-15", "2026-10-28"), self._fechas(self.obreros))

    def test_sin_periodos_propone_el_periodo_en_curso(self):
        hoy = date(2026, 10, 28)   # miercoles
        semanal = PayrollGroupService.create({"group_name": "Semanal", "pay_frequency": "weekly"}, user_id=1)
        mensual = PayrollGroupService.create({"group_name": "Mensual", "pay_frequency": "monthly"}, user_id=1)
        self.assertEqual(("2026-10-26", "2026-11-01"), self._fechas(semanal["id_payroll_group"], hoy))
        self.assertEqual(("2026-10-01", "2026-10-31"), self._fechas(mensual["id_payroll_group"], hoy))
        self.assertEqual(("2026-10-16", "2026-10-31"), self._fechas(self.general, hoy))

    def _fechas(self, grupo, hoy=None):
        propuesta = siguiente_periodo(grupo, hoy)
        return propuesta["period_start"], propuesta["period_end"]


class TestValidaciones(_ConGrupos):
    def test_las_vigencias_de_una_persona_no_se_enciman(self):
        with self.assertRaises(AppError) as error:
            EmployeePayrollGroupService.create({"id_user": 74, "id_payroll_group": self.general,
                                                "valid_from": "2026-06-01"}, user_id=1)
        self.assertEqual("errors.employee_payroll_group_overlap", error.exception.message_key)

    def test_la_periodicidad_debe_ser_una_conocida(self):
        with self.assertRaises(AppError):
            PayrollGroupService.create({"group_name": "Diario", "pay_frequency": "daily"}, user_id=1)

    def test_siempre_hay_un_grupo_por_omision(self):
        for accion in (lambda: PayrollGroupService.delete(self.general, user_id=1),
                       lambda: PayrollGroupService.update(self.general, {"is_default": False}, user_id=1)):
            with self.assertRaises(AppError) as error:
                accion()
            self.assertEqual("errors.payroll_group_default_required", error.exception.message_key)

    def test_marcar_otro_por_omision_desmarca_al_anterior(self):
        PayrollGroupService.update(self.obreros, {"is_default": True}, user_id=1)
        self.assertFalse(PayrollGroupService.get(self.general)["is_default"])
        self.assertTrue(PayrollGroupService.get(self.obreros)["is_default"])

    def test_un_grupo_con_empleados_no_se_borra(self):
        with self.assertRaises(AppError) as error:
            PayrollGroupService.delete(self.obreros, user_id=1)
        self.assertEqual("errors.payroll_group_in_use", error.exception.message_key)
