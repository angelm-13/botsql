"""Hoja de nomina tipo Excel (puntos 6 y 7 de RH, 2026-11-04).

Usa el periodo 5 de _ConPeriodoDePrueba (Ana, diario 500, 3 dias checados). Lo
que da la hoja se compara con el camino que ya existia: capturar el movimiento a
mano y calcular. Asi se prueba que la hoja no tiene reglas propias.
"""
from __future__ import annotations

import io
import zipfile

import jwt

from app.models import EntityPermission, PayrollConcept, PayrollMovement, PayrollPeriod
from app.models.session import transaction_context
from app.services.payroll_calculation_service import calcular_periodo
from app.services.payroll_sheet_service import guardar, hoja, simular, xlsx
from app.utils.auth import SECRET_KEY
from app.utils.errors import AppError
from tests.test_services.test_payroll_calculation_service import _ConPeriodoDePrueba

ANA = 71
TITULOS = {"employee": "Empleado", "days": "Dias", "earnings": "Total ingresos", "deductions": "Total egresos",
           "net": "Neto", "totals": "TOTALES"}


class _ConHoja(_ConPeriodoDePrueba):
    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            bono = PayrollConcept(payroll_code="BONO_NAV", payroll_concept_description="Bono navidad", type="earning",
                                  is_taxable=True, is_imss=False, created_by=1)
            prestamo = PayrollConcept(payroll_code="PRESTAMO", payroll_concept_description="Prestamo", type="deduction",
                                      is_taxable=False, is_imss=False, created_by=1)
            db.add_all([bono, prestamo])
            db.flush()
            self.bono, self.prestamo = bono.id_payroll_concept, prestamo.id_payroll_concept
        calcular_periodo(5, 1)

    def fila(self, datos):
        return next(r for r in datos["rows"] if r["id_user"] == ANA)

    def vivos(self, concepto):
        with transaction_context() as db:
            return [float(m.amount) for m in db.query(PayrollMovement).filter(
                PayrollMovement.id_payroll_concept == concepto, PayrollMovement.deletion_date.is_(None))]


class TestHoja(_ConHoja):
    def test_columnas_calculadas_y_conceptos_para_agregar(self):
        datos = hoja(5)
        columnas = {c["code"]: c for c in datos["columns"]}
        self.assertEqual({"SUELDO", "ISR", "IMSS"} <= set(columnas), True)
        self.assertFalse(columnas["SUELDO"]["editable"])
        self.assertEqual({"BONO_NAV", "PRESTAMO"}, {c["code"] for c in datos["available"]})
        self.assertEqual(["earning", "deduction"], sorted({c["type"] for c in datos["columns"]}, reverse=True))
        ana = self.fila(datos)
        self.assertEqual(ana["net_pay"], round(ana["total_earnings"] - ana["total_deductions"], 2))
        self.assertEqual(datos["totals"]["net_pay"], ana["net_pay"])

    def test_guardar_da_lo_mismo_que_capturar_a_mano_y_calcular(self):
        datos = guardar(5, [{"id_user": ANA, "id_payroll_concept": self.bono, "amount": "300"},
                            {"id_user": ANA, "id_payroll_concept": self.prestamo, "amount": 250}], user_id=1)
        ana = self.fila(datos)
        # El mismo resultado por el camino de siempre (y recalcular no cambia nada).
        a_mano = calcular_periodo(5, 1)["employees"][0]
        self.assertEqual((a_mano["total_earnings"], a_mano["total_deductions"], a_mano["net_pay"]),
                         (ana["total_earnings"], ana["total_deductions"], ana["net_pay"]))
        self.assertEqual((300.0, 250.0), (ana["amounts"][str(self.bono)], ana["amounts"][str(self.prestamo)]))
        # El bono grava: sube la base del ISR en 300.
        self.assertEqual(300.0, round(a_mano["taxable_income"] - self._sin_bono_gravable(), 2))
        self.assertEqual({"BONO_NAV", "PRESTAMO"} <= {c["code"] for c in datos["columns"]}, True)
        self.assertEqual([], datos["available"])

    def _sin_bono_gravable(self):
        with transaction_context() as db:
            for m in db.query(PayrollMovement).filter(PayrollMovement.id_payroll_concept == self.bono,
                                                      PayrollMovement.deletion_date.is_(None)):
                m.deletion_date = m.creation_date
        return calcular_periodo(5, 1)["employees"][0]["taxable_income"]

    def test_reescribir_reemplaza_y_cero_quita(self):
        guardar(5, [{"id_user": ANA, "id_payroll_concept": self.bono, "amount": 300}], user_id=1)
        guardar(5, [{"id_user": ANA, "id_payroll_concept": self.bono, "amount": 450}], user_id=1)
        self.assertEqual([450.0], self.vivos(self.bono))
        datos = guardar(5, [{"id_user": ANA, "id_payroll_concept": self.bono, "amount": ""}], user_id=1)
        self.assertEqual([], self.vivos(self.bono))
        self.assertNotIn(str(self.bono), self.fila(datos)["amounts"])

    def test_simular_no_guarda_nada(self):
        antes = hoja(5)
        sim = simular(5, [{"id_user": ANA, "id_payroll_concept": self.bono, "amount": 300}], user_id=1)
        self.assertTrue(sim["simulated"])
        self.assertEqual(round(self.fila(antes)["total_earnings"] + 300, 2), self.fila(sim)["total_earnings"])
        self.assertEqual([], self.vivos(self.bono))
        self.assertEqual(antes["rows"], hoja(5)["rows"])
        # Pasar a la nomina = guardar lo mismo: queda igual que lo simulado.
        self.assertEqual(self.fila(sim)["net_pay"], self.fila(guardar(5, [
            {"id_user": ANA, "id_payroll_concept": self.bono, "amount": 300}], user_id=1))["net_pay"])

    def test_lo_que_no_se_puede(self):
        with transaction_context() as db:
            sueldo = db.query(PayrollConcept).filter(PayrollConcept.payroll_code == "SUELDO").one().id_payroll_concept
        casos = [
            ([{"id_user": ANA, "id_payroll_concept": sueldo, "amount": 1}], "errors.payroll_sheet_concept_calculated"),
            ([{"id_user": ANA, "id_payroll_concept": self.bono, "amount": -1}], "errors.invalid_field"),
            ([{"id_user": ANA, "id_payroll_concept": self.bono, "amount": "x"}], "errors.invalid_field"),
            ([], "errors.invalid_field"),
            ([{"id_user": 72, "id_payroll_concept": self.bono, "amount": 1}], "errors.resource_not_found"),
        ]
        for cambios, llave in casos:
            with self.subTest(llave=llave), self.assertRaises(AppError) as error:
                guardar(5, cambios, user_id=1)
            self.assertEqual(llave, error.exception.message_key)
        with transaction_context() as db:
            db.get(PayrollPeriod, 5).period_state = "closed"
        for funcion in (guardar, simular):
            with self.assertRaises(AppError) as error:
                funcion(5, [{"id_user": ANA, "id_payroll_concept": self.bono, "amount": 1}], user_id=1)
            self.assertEqual("errors.payroll_period_closed", error.exception.message_key)
        with transaction_context() as db:
            db.get(PayrollPeriod, 5).period_state = "open"
        with self.assertRaises(AppError) as error:
            guardar(5, [{"id_user": ANA, "id_payroll_concept": self.bono, "amount": 1}], user_id=1)
        self.assertEqual("errors.payroll_period_not_calculated", error.exception.message_key)

    def test_excel(self):
        guardar(5, [{"id_user": ANA, "id_payroll_concept": self.prestamo, "amount": 250}], user_id=1)
        contenido, nombre = xlsx(5, TITULOS)
        self.assertEqual("nomina_periodo_5.xlsx", nombre)
        hoja_xml = zipfile.ZipFile(io.BytesIO(contenido)).read("xl/worksheets/sheet1.xml").decode()
        for texto in ("Ana", "Prestamo", "Sueldo", "TOTALES", "<v>250.0</v>"):
            self.assertIn(texto, hoja_xml)


class TestRutas(_ConHoja):
    """Ver pide leer el detalle de nomina; escribir, ademas los movimientos (el Gestor)."""

    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            for entidad, crear, leer, editar in (("payroll_detail", 4, 4, 0), ("payroll_movement", 0, 4, 0)):
                db.add(EntityPermission(id_permission=983, entity_name=entidad, scope_create=crear,
                                        scope_read=leer, scope_update=editar, scope_delete=0, created_by=1))

    def h(self, permiso):
        token = jwt.encode({"id_user": 1, "id_permission": permiso}, SECRET_KEY, algorithm="HS256")
        return {"Authorization": f"Bearer {token}"}

    def test_ver_simular_y_descargar_con_lectura(self):
        self.assertEqual(200, self.client.get("/payroll_period/5/sheet", headers=self.h(983)).status_code)
        cuerpo = {"changes": [{"id_user": ANA, "id_payroll_concept": self.bono, "amount": 10}]}
        self.assertEqual(200, self.client.post("/payroll_period/5/sheet/simulate", headers=self.h(983),
                                               json=cuerpo).status_code)
        r = self.client.get("/payroll_period/5/sheet.xlsx", headers=self.h(983))
        self.assertEqual((200, "attachment"), (r.status_code, r.headers["Content-Disposition"].split(";")[0]))
        self.assertEqual(403, self.client.get("/payroll_period/5/sheet", headers=self.h(984)).status_code)

    def test_escribir_sin_permiso_de_movimientos(self):
        r = self.client.post("/payroll_period/5/sheet", headers=self.h(983),
                             json={"changes": [{"id_user": ANA, "id_payroll_concept": self.bono, "amount": 10}]})
        self.assertEqual(403, r.status_code)
        self.assertEqual([], self.vivos(self.bono))


class TestPrestaciones(_ConHoja):
    """Prestaciones que la empresa activa (respuestas de RH, 2026-11-04)."""

    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            infonavit = PayrollConcept(payroll_code="PR_INFONAVIT", payroll_concept_description="Crédito Infonavit",
                                       type="deduction", is_taxable=False, is_imss=False, created_by=1)
            db.add(infonavit)
            db.flush()
            self.infonavit = infonavit.id_payroll_concept

    def activar(self):
        from datetime import date
        from app.models import PayrollParameter
        with transaction_context() as db:
            db.add(PayrollParameter(parameter_key="benefit_infonavit", value=1, valid_from=date(2026, 1, 1),
                                    created_by=1))

    def test_apagada_no_se_ofrece_ni_se_escribe(self):
        self.assertNotIn("PR_INFONAVIT", {c["code"] for c in hoja(5)["available"]})
        with self.assertRaises(AppError) as error:
            guardar(5, [{"id_user": ANA, "id_payroll_concept": self.infonavit, "amount": 300}], user_id=1)
        self.assertEqual("errors.payroll_benefit_disabled", error.exception.message_key)

    def test_activa_se_ofrece_y_descuenta_sin_tocar_el_isr(self):
        self.activar()
        self.assertIn("PR_INFONAVIT", {c["code"] for c in hoja(5)["available"]})
        antes = self.fila(hoja(5))
        despues = self.fila(guardar(5, [{"id_user": ANA, "id_payroll_concept": self.infonavit, "amount": 300}], user_id=1))
        self.assertEqual(round(antes["total_deductions"] + 300, 2), despues["total_deductions"])
        self.assertEqual(round(antes["net_pay"] - 300, 2), despues["net_pay"])
