"""Simulador de nomina (diseño aprobado por RH el 2026-11-03).

Cifras de 2026 de tests/fixtures/cifras_nomina_2026.py, al 15 de octubre:
UMA 117.31, minimo 315.04, tarifa quincenal. Diario 500, ingreso 2024-03-01
(tercer año: 16 dias de vacaciones, factor 1 + (15 + 16 x 25 %)/365 = 1.0521,
SBC 526.05). IMSS por dia: 526.05 x 2.375 % + (526.05 - 351.93) x 0.40 % = 13.19017.

Quincena sin incidencias:
  Sueldo 500 x 15 = 7,500.00. ISR: 660.75 + (7,500 - 7,225.96) x 17.92 % = 709.86;
  sin subsidio (llevado a mes pasa del limite). IMSS 13.19017 x 15 = 197.85.
  Neto 6,592.29.
Con 2 faltas, 3 horas dobles, 1 triple, 1 domingo y "Premio disfraz Halloween" de 1,000:
  Sueldo 500 x 13 = 6,500. Hora 500 / 8 = 62.50: dobles 375.00 (exenta la mitad,
  187.50) y triple 187.50 -> horas extra 562.50, gravan 375.00. Prima dominical
  125.00, grava 125 - 117.31 = 7.69. El bono grava completo.
  Gravable 6,500 + 375 + 7.69 + 1,000 = 7,882.69 -> ISR 660.75 + 656.73 x 17.92 % = 778.44.
  IMSS 13 dias: 171.47. Percepciones 8,187.50; neto 7,237.59.
"""
from __future__ import annotations

from datetime import date

import jwt

from app.models import EntityPermission, PayrollConcept, PayrollMovement, PayrollPeriod
from app.models.session import transaction_context
from app.services.payroll_calculation_service import calcular_periodo
from app.services.payroll_simulator_service import pasar_bonos, simular
from app.utils.auth import SECRET_KEY
from app.utils.errors import AppError
from tests.test_services.test_payroll_calculation_service import _ConPeriodoDePrueba

BASE = {"date": "2026-10-15", "pay_frequency": "semimonthly", "salary_type": "daily", "amount": "500",
        "hire_date": "2024-03-01"}
ANA = 71


def _de(conceptos):
    return {c["description"]: c["amount"] for c in conceptos}


class TestSimulacion(_ConPeriodoDePrueba):
    def test_quincena_sin_incidencias(self):
        r = simular(BASE)
        self.assertEqual({"Sueldo": 7500.0}, _de(r["earnings"]))
        self.assertEqual((709.86, 197.85, 6592.29), (r["deductions"][0]["amount"], r["deductions"][1]["amount"],
                                                       r["net_pay"]))
        self.assertEqual((1.0521, 526.05, 0.0), (r["integration_factor"], r["sbc"], r["employment_subsidy"]))

    def test_faltas_horas_extra_domingo_y_un_bono(self):
        r = simular({**BASE, "absences": 2, "overtime_double_hours": 3, "overtime_triple_hours": 1,
                     "sundays_worked": 1, "bonuses": [{"name": "Premio disfraz Halloween", "amount": "1000"}]})
        self.assertEqual({"Sueldo": 6500.0, "Horas extra": 562.5, "Prima dominical": 125.0,
                          "Premio disfraz Halloween": 1000.0}, _de(r["earnings"]))
        self.assertEqual((7882.69, 778.44, 171.47, 8187.5, 7237.59),
                         (r["taxable_income"], _de(r["deductions"])["ISR retenido (subsidio para el empleo aplicado)"],
                          _de(r["deductions"])["Cuota obrera IMSS"], r["total_earnings"], r["net_pay"]))

    def test_fijo_de_la_misma_periodicidad_descuenta_las_faltas_y_por_hora_usa_la_jornada(self):
        fijo = simular({**BASE, "salary_type": "fixed", "amount": "7500", "fixed_frequency": "semimonthly",
                        "absences": 1})
        self.assertEqual((500.0, 7000.0), (fijo["daily_salary"], _de(fijo["earnings"])["Sueldo"]))
        hora = simular({**BASE, "salary_type": "hourly", "amount": "60", "day_hours": "9"})
        self.assertEqual((540.0, 60.0, 8100.0), (hora["daily_salary"], hora["hour_price"], _de(hora["earnings"])["Sueldo"]))

    def test_datos_invalidos(self):
        for malo in ({**BASE, "pay_frequency": "diario"}, {**BASE, "amount": "0"}, {**BASE, "absences": 16},
                     {**BASE, "bonuses": [{"name": "", "amount": 10}]}, {**BASE, "overtime_double_hours": "-1"}):
            with self.assertRaises(AppError):
                simular(malo)


class TestPasarBonos(_ConPeriodoDePrueba):
    def test_el_bono_queda_en_su_periodo_y_sale_en_el_calculo(self):
        antes = calcular_periodo(5, 1)["employees"][0]
        pasar_bonos({"id_user": ANA, "id_payroll_period": 5,
                     "bonuses": [{"name": "Premio disfraz Halloween", "amount": "500"}]}, user_id=1)
        despues = calcular_periodo(5, 1)["employees"][0]
        self.assertEqual((500.0, 500.0), (round(despues["taxable_income"] - antes["taxable_income"], 2),
                                          round(despues["total_earnings"] - antes["total_earnings"], 2)))
        with transaction_context() as db:
            concepto = db.query(PayrollConcept).filter(PayrollConcept.payroll_code == "BONO").one()
            self.assertEqual(("Premio disfraz Halloween", True, False),
                             (concepto.payroll_concept_description, concepto.is_taxable, concepto.is_imss))
            self.assertEqual(1, db.query(PayrollMovement).filter(
                PayrollMovement.id_payroll_concept == concepto.id_payroll_concept).count())

    def test_no_en_un_periodo_cerrado(self):
        with transaction_context() as db:
            db.get(PayrollPeriod, 5).period_state = "closed"
        with self.assertRaises(AppError) as error:
            pasar_bonos({"id_user": ANA, "id_payroll_period": 5, "bonuses": [{"name": "Bono", "amount": 1}]}, user_id=1)
        self.assertEqual("errors.payroll_period_closed", error.exception.message_key)


class TestRutas(_ConPeriodoDePrueba):
    """Simular pide la capacidad del Gestor; pasar los bonos, ademas el alta de movimientos."""

    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.add(EntityPermission(id_permission=981, entity_name="payroll_simulator", scope_create=0,
                                    scope_read=4, scope_update=0, scope_delete=0, created_by=1))

    def h(self, permiso):
        token = jwt.encode({"id_user": 1, "id_permission": permiso}, SECRET_KEY, algorithm="HS256")
        return {"Authorization": f"Bearer {token}"}

    def test_simular_con_la_capacidad_y_sin_ella(self):
        self.assertEqual(200, self.client.post("/payroll_simulator/calculate", headers=self.h(981), json=BASE).status_code)
        self.assertEqual(403, self.client.post("/payroll_simulator/calculate", headers=self.h(982), json=BASE).status_code)

    def test_pasar_bonos_sin_permiso_de_movimientos(self):
        r = self.client.post("/payroll_simulator/bonuses", headers=self.h(981),
                             json={"id_user": ANA, "id_payroll_period": 5, "bonuses": [{"name": "Bono", "amount": 1}]})
        self.assertEqual(403, r.status_code)
