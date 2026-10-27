"""Aguinaldo (LFT art. 87) y prima vacacional (LFT art. 80) con su exencion de
ISR (LISR art. 93 fr. XIV), con resultados calculados a mano.

Cuenta de Ana en el periodo 5 (quincena 1-15 oct 2026, salario diario 500,
3 dias checados, ingreso 2025-10-03: cumple su primer año el 3 de octubre):
  sueldo 1,500.00
  aguinaldo 500 x 15 = 7,500.00 (año completo); exento 30 x 117.31 = 3,519.30,
    gravado 3,980.70
  prima 12 dias x 500 x 25% = 1,500.00; exento 15 x 117.31 = 1,759.65 -> gravado 0
  base ISR 1,500 + 3,980.70 = 5,480.70
  ISR quincenal 207.75 + (5,480.70 - 3,537.16) x 10.88% = 419.21; llevado a mes
    (11,107.62) no pasa el limite: subsidio 264.30 -> ISR 154.91
  IMSS: 1 año cumplido, 14 dias de vacaciones, factor 1.0507, SBC 525.35,
    cuota 13.1707/dia x 3 = 39.51
  percepciones 10,500.00; deducciones 194.42; neto 10,305.58
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import jwt

from app.models import EntityPermission, Field, NmFieldPermission, PayrollConcept, PayrollMovement, PayrollPeriod, User
from app.models.session import transaction_context
from app.services import payroll_tax_rules as ley
from app.services.payroll_calculation_service import calcular_periodo
from app.utils.auth import SECRET_KEY
from tests.conftest import BackendTestCase
from tests.test_services.test_payroll_calculation_service import _ConPeriodoDePrueba


class TestReglas(BackendTestCase):

    def test_aguinaldo_de_un_anio_completo(self):
        self.assertEqual(Decimal("6750.00"), ley.aguinaldo(450, 15, date(2020, 3, 1), 2026))
        self.assertEqual(Decimal("6750.00"), ley.aguinaldo(450, 15, None, 2026))

    def test_aguinaldo_proporcional_si_entro_en_el_anio(self):
        # Del 1 de julio al 31 de diciembre son 184 dias: 6,750 x 184 / 365 = 3,402.74.
        self.assertEqual(Decimal("3402.74"), ley.aguinaldo(450, 15, date(2026, 7, 1), 2026))
        self.assertEqual(Decimal("0.00"), ley.aguinaldo(450, 15, date(2027, 1, 5), 2026))

    def test_solo_grava_lo_que_pasa_del_tope(self):
        self.assertEqual(Decimal("3230.70"), ley.parte_gravada(6750, "117.31", 30))
        self.assertEqual(Decimal("0.00"), ley.parte_gravada(1350, "117.31", 15))

    def test_prima_segun_los_anios_cumplidos(self):
        self.assertEqual((12, Decimal("1350.00")), ley.prima_vacacional(450, 1, 25))
        # Al cumplir 6 años el año que termino fue el sexto: 22 dias.
        self.assertEqual((22, Decimal("2475.00")), ley.prima_vacacional(450, 6, 25))
        self.assertEqual((0, Decimal("0.00")), ley.prima_vacacional(450, 0, 25))

    def test_aniversario_dentro_del_periodo(self):
        self.assertEqual(date(2026, 10, 3),
                         ley.aniversario_en(date(2025, 10, 3), date(2026, 10, 1), date(2026, 10, 15)))
        # El propio dia de ingreso no es aniversario.
        self.assertIsNone(ley.aniversario_en(date(2026, 10, 3), date(2026, 10, 1), date(2026, 10, 15)))
        self.assertIsNone(ley.aniversario_en(None, date(2026, 10, 1), date(2026, 10, 15)))
        # Quien entro un 29 de febrero cumple el 28 en años no bisiestos.
        self.assertEqual(date(2026, 2, 28),
                         ley.aniversario_en(date(2024, 2, 29), date(2026, 2, 16), date(2026, 2, 28)))


class TestEnElCalculo(_ConPeriodoDePrueba):

    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.get(User, 71).hire_date = date(2025, 10, 3)
            db.get(PayrollPeriod, 5).includes_aguinaldo = True

    def test_aguinaldo_y_prima_en_la_quincena(self):
        ana = calcular_periodo(5, 1)["employees"][0]

        self.assertEqual(1500.0, ana["salary"])
        self.assertEqual(7500.0, ana["aguinaldo"])
        self.assertEqual(3980.70, ana["aguinaldo_taxable"])
        self.assertEqual(12, ana["vacation_premium_days"])
        self.assertEqual(1500.0, ana["vacation_premium"])
        self.assertEqual(0.0, ana["vacation_premium_taxable"])
        self.assertEqual(5480.70, ana["taxable_income"])
        self.assertEqual(419.21, ana["isr_before_subsidy"])
        self.assertEqual(264.30, ana["employment_subsidy"])
        self.assertEqual(154.91, ana["isr"])
        self.assertEqual(525.35, ana["sbc"])
        self.assertEqual(39.51, ana["imss"])
        self.assertEqual(10500.0, ana["total_earnings"])
        self.assertEqual(194.42, ana["total_deductions"])
        self.assertEqual(10305.58, ana["net_pay"])

    def test_sin_la_casilla_no_hay_aguinaldo_y_recalcular_lo_quita(self):
        calcular_periodo(5, 1)
        with transaction_context() as db:
            db.get(PayrollPeriod, 5).includes_aguinaldo = False
        ana = calcular_periodo(5, 1)["employees"][0]

        self.assertEqual(0.0, ana["aguinaldo"])
        self.assertEqual(1500.0, ana["vacation_premium"])   # la prima no depende de la casilla
        with transaction_context() as db:
            codigos = [c for (c,) in db.query(PayrollConcept.payroll_code)
                       .join(PayrollMovement, PayrollMovement.id_payroll_concept == PayrollConcept.id_payroll_concept)
                       .filter(PayrollMovement.deletion_date.is_(None))]
        self.assertNotIn("AGUINALDO", codigos)
        self.assertEqual(1, codigos.count("PRIMA_VAC"))

    def test_sin_aniversario_en_el_periodo_no_hay_prima(self):
        with transaction_context() as db:
            db.get(User, 71).hire_date = date(2025, 11, 20)
        ana = calcular_periodo(5, 1)["employees"][0]
        self.assertEqual(0.0, ana["vacation_premium"])

    def test_marcar_el_concepto_como_gravable_no_lo_cobra_dos_veces(self):
        calcular_periodo(5, 1)
        with transaction_context() as db:
            db.query(PayrollConcept).filter_by(payroll_code="AGUINALDO").one().is_taxable = True
        ana = calcular_periodo(5, 1)["employees"][0]
        self.assertEqual(5480.70, ana["taxable_income"])

    def test_sin_fecha_de_ingreso_paga_el_anio_completo_y_avisa(self):
        with transaction_context() as db:
            db.get(User, 71).hire_date = None
        resultado = calcular_periodo(5, 1)
        ana = resultado["employees"][0]
        self.assertEqual(7500.0, ana["aguinaldo"])
        self.assertEqual(0.0, ana["vacation_premium"])
        self.assertEqual(["Ana"], [e["full_name"] for e in resultado["without_hire_date"]])

    def test_el_recibo_y_el_resumen_los_muestran(self):
        calcular_periodo(5, 1)
        from app.services.payroll_calculation_service import datos_del_recibo, resumen_periodo
        recibo = datos_del_recibo(5, 71)
        self.assertEqual({"SUELDO": 1500.0, "AGUINALDO": 7500.0, "PRIMA_VAC": 1500.0},
                         {m["code"]: m["amount"] for m in recibo["earnings"]})
        ana = resumen_periodo(5)["employees"][0]
        self.assertEqual((7500.0, 1500.0), (ana["aguinaldo"], ana["vacation_premium"]))

    def test_la_casilla_se_guarda_y_regresa_por_la_api(self):
        # La ruta solo devuelve los campos de su lista ALLOWED_FIELDS: sin el
        # campo nuevo ahi, se guardaba pero la pantalla lo volvia a ver apagado.
        with transaction_context() as db:
            db.add(EntityPermission(id_permission=901, entity_name="payroll_period", scope_create=4,
                                    scope_read=4, scope_update=4, scope_delete=4, created_by=1))
            # Permiso de CAMPO para leer y escribir la casilla (user_type ya no da acceso).
            campo = Field(table_name="payroll_period", field_name="includes_aguinaldo", created_by=1)
            db.add(campo)
            db.flush()
            db.add(NmFieldPermission(id_field=campo.id_field, id_permission=901, control_type="7", created_by=1))
        token = jwt.encode({"id_user": 1, "id_permission": 901}, SECRET_KEY, algorithm="HS256")
        headers = {"Authorization": f"Bearer {token}"}
        respuesta = self.client.put("/payroll_period/5", json={"includes_aguinaldo": False}, headers=headers)
        self.assertEqual(200, respuesta.status_code)
        self.assertIs(False, self.json(respuesta)["includes_aguinaldo"])
        self.assertIs(False, self.json(self.client.get("/payroll_period/5", headers=headers))["includes_aguinaldo"])
