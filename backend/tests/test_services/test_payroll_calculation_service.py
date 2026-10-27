"""Calculo de la nomina de un periodo con las checadas guardadas.

Regla: sueldo = salario diario x dias con al menos una checada ligada al
empleado; ISR (con subsidio) e IMSS se descuentan con las cifras oficiales 2026;
el neto suma todos los movimientos (los capturados a mano tambien) y recalcular
no duplica.

Cuenta de Ana (salario diario 500, 3 dias en una quincena de 15 dias):
  sueldo 1,500.00
  ISR quincenal: 7.95 + (1,500 - 416.71) x 6.40% = 77.28; subsidio 264.30 -> ISR 0
  IMSS: factor 1.0493 (primer año), SBC 524.65, cuota 13.1513/dia x 3 = 39.45
  neto 1,500.00 - 39.45 = 1,460.55
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import jwt

from app.models import (AttendanceRecord, EntityPermission, PayrollConcept, PayrollDetail, PayrollIsrBracket,
                        PayrollMovement, PayrollParameter, PayrollPeriod, User)
from app.models.session import transaction_context
from app.services.payroll_calculation_service import calcular_periodo
from app.utils.auth import SECRET_KEY
from tests.conftest import BackendTestCase
from tests.fixtures.cifras_nomina_2026 import sembrar_cifras_2026


def dar_todos_los_campos(db, id_permission, tablas):
    """Permiso de CAMPO sobre todas las columnas: user_type ya no da acceso a campos (390e0dc)."""
    from app.models import Field, NmFieldPermission
    from app.models.base import Base
    for tabla in tablas:
        for columna in Base.metadata.tables[tabla].columns:
            campo = Field(table_name=tabla, field_name=columna.name, created_by=1)
            db.add(campo)
            db.flush()
            db.add(NmFieldPermission(id_field=campo.id_field, id_permission=id_permission, control_type="7",
                                     created_by=1))


def _checada(id_user, cuando, n):
    return AttendanceRecord(id_user=id_user, employee_no=str(id_user), check_time=cuando,
                            source="kronos", source_ref=f"t:{n}", created_by=1)


class _ConPeriodoDePrueba(BackendTestCase):
    """Ana (salario diario 500) con 3 dias checados en el periodo 5; Luis sin salario."""

    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            sembrar_cifras_2026(db)
            for id_user, nombre, diario, empleado in (
                (71, "Ana", Decimal("500.00"), True),
                (72, "Luis", None, True),            # empleado sin salario capturado
                (73, "Admin", Decimal("900.00"), False),  # no es empleado
            ):
                db.add(User(id_user=id_user, created_by=1, full_name=nombre, id_permission=1,
                            id_proyect=1, id_status=1, supervisor=1, user_type="employee",
                            is_employee=empleado, base_salary=diario, username=f"u{id_user}"))
            db.add(PayrollPeriod(id_payroll_period=5, period_start=date(2026, 10, 1),
                                 period_end=date(2026, 10, 15), payment_date=date(2026, 10, 15),
                                 id_status=1, created_by=1))
            n = 0
            # Ana checa entrada y salida 3 dias del periodo, y 1 dia fuera de el.
            for dia in (1, 2, 5, 20):
                for hora in (8, 17):
                    n += 1
                    db.add(_checada(71, datetime(2026, 10, dia, hora, 0), n))


class TestCalcularPeriodo(_ConPeriodoDePrueba):

    def test_el_sueldo_es_salario_diario_por_dias_trabajados(self):
        resultado = calcular_periodo(5, 1)

        self.assertEqual(1, len(resultado["employees"]))
        ana = resultado["employees"][0]
        self.assertEqual(3, ana["days_worked"])     # el dia 20 queda fuera del periodo
        self.assertEqual(1500.0, ana["salary"])
        self.assertEqual(77.28, ana["isr_before_subsidy"])
        self.assertEqual(264.30, ana["employment_subsidy"])
        self.assertEqual(0.0, ana["isr"])
        self.assertEqual(524.65, ana["sbc"])
        self.assertEqual(39.45, ana["imss"])
        self.assertEqual(1460.55, ana["net_pay"])
        self.assertEqual(["Luis"], [e["full_name"] for e in resultado["without_salary"]])

    def test_recalcular_no_duplica_el_sueldo(self):
        calcular_periodo(5, 1)
        calcular_periodo(5, 1)
        with transaction_context() as db:
            self.assertEqual(1, db.query(PayrollDetail).filter_by(id_payroll_period=5).count())
            vivos = db.query(PayrollMovement).filter(PayrollMovement.deletion_date.is_(None)).count()
            # SUELDO e IMSS (el ISR quedo en cero por el subsidio y no se escribe).
            self.assertEqual(2, vivos)

    def test_lo_capturado_a_mano_se_respeta_y_entra_al_neto(self):
        calcular_periodo(5, 1)
        with transaction_context() as db:
            detalle = db.query(PayrollDetail).filter_by(id_payroll_period=5).one()
            bono = PayrollConcept(payroll_code="BONO", payroll_concept_description="Bono",
                                  type="earning", is_taxable=True, is_imss=False, created_by=1)
            descuento = PayrollConcept(payroll_code="DESC", payroll_concept_description="Descuento",
                                       type="deduction", is_taxable=False, is_imss=False, created_by=1)
            patronal = PayrollConcept(payroll_code="PAT", payroll_concept_description="Patronal",
                                      type="employer_contribution", is_taxable=False, is_imss=True, created_by=1)
            db.add_all([bono, descuento, patronal])
            db.flush()
            for concepto, monto in ((bono, "200"), (descuento, "100"), (patronal, "999")):
                db.add(PayrollMovement(id_payroll_detail=detalle.id_payroll_detail,
                                       id_payroll_concept=concepto.id_payroll_concept,
                                       amount=Decimal(monto), created_by=1))

        ana = calcular_periodo(5, 1)["employees"][0]

        self.assertEqual(1700.0, ana["total_earnings"])   # sueldo 1500 + bono 200
        self.assertEqual(1700.0, ana["taxable_income"])   # el bono grava ISR
        self.assertEqual(139.45, ana["total_deductions"])  # descuento 100 + IMSS 39.45
        self.assertEqual(1560.55, ana["net_pay"])          # la aportacion patronal no entra

    def test_sin_checadas_el_sueldo_es_cero(self):
        with transaction_context() as db:
            db.query(AttendanceRecord).delete()
        ana = calcular_periodo(5, 1)["employees"][0]
        self.assertEqual(0, ana["days_worked"])
        self.assertEqual(0.0, ana["net_pay"])

    def test_la_ruta_exige_permiso_y_calcula(self):
        with transaction_context() as db:
            db.add(EntityPermission(id_permission=701, entity_name="payroll_detail",
                                    scope_create=4, scope_read=4, scope_update=4, scope_delete=0,
                                    created_by=1))

        def headers(id_permission):
            token = jwt.encode({"id_user": 41, "id_permission": id_permission}, SECRET_KEY, algorithm="HS256")
            return {"Authorization": f"Bearer {token}"}

        self.assertEqual(403, self.client.post("/payroll_period/5/calculate", headers=headers(999)).status_code)
        respuesta = self.client.post("/payroll_period/5/calculate", headers=headers(701))
        self.assertEqual(200, respuesta.status_code)
        self.assertEqual(1460.55, self.json(respuesta)["total_net_pay"])
        self.assertEqual(404, self.client.post("/payroll_period/999/calculate", headers=headers(701)).status_code)


class TestCierreDelPeriodo(_ConPeriodoDePrueba):
    """Abierto -> Calculado -> Cerrado; cerrado queda congelado; solo administracion reabre."""

    def _headers(self, id_permission, id_user=41, **extra):
        token = jwt.encode({"id_user": id_user, "id_permission": id_permission, **extra}, SECRET_KEY, algorithm="HS256")
        return {"Authorization": f"Bearer {token}"}

    def _permisos(self):
        with transaction_context() as db:
            for entidad in ("payroll_period", "payroll_detail", "payroll_movement"):
                # 801 administra nomina; 802 la opera pero no puede borrar (ni reabrir).
                db.add(EntityPermission(id_permission=801, entity_name=entidad, scope_create=4,
                                        scope_read=4, scope_update=4, scope_delete=4, created_by=1))
                db.add(EntityPermission(id_permission=802, entity_name=entidad, scope_create=4,
                                        scope_read=4, scope_update=4, scope_delete=0, created_by=1))
            dar_todos_los_campos(db, 801, ("payroll_period", "payroll_detail", "payroll_movement"))

    def _estado(self):
        with transaction_context() as db:
            return db.get(PayrollPeriod, 5).period_state

    def test_un_periodo_nace_abierto_y_calcular_lo_pasa_a_calculado(self):
        from app.services.payroll_calculation_service import resumen_periodo
        self.assertEqual("open", self._estado())
        calcular_periodo(5, 1)
        self.assertEqual("calculated", self._estado())
        self.assertEqual(3, resumen_periodo(5)["employees"][0]["days_worked"])

    def test_no_se_cierra_lo_que_no_se_ha_calculado(self):
        from app.services.payroll_calculation_service import cerrar_periodo
        from app.utils.errors import AppError
        with self.assertRaises(AppError) as error:
            cerrar_periodo(5, 1)
        self.assertEqual(409, error.exception.status_code)

    def test_cerrado_no_se_recalcula_y_guarda_quien_lo_cerro(self):
        from app.services.payroll_calculation_service import cerrar_periodo
        from app.utils.errors import AppError
        calcular_periodo(5, 1)
        cerrado = cerrar_periodo(5, 7)
        self.assertEqual("closed", cerrado["period_state"])
        self.assertEqual(7, cerrado["closed_by"])
        self.assertIsNotNone(cerrado["closed_at"])
        with self.assertRaises(AppError) as error:
            calcular_periodo(5, 1)
        self.assertEqual("errors.payroll_period_closed", error.exception.message_key)

    def test_cerrado_nada_se_edita_por_la_api(self):
        from app.services.payroll_calculation_service import cerrar_periodo
        self._permisos()
        calcular_periodo(5, 1)
        with transaction_context() as db:
            detalle = db.query(PayrollDetail).filter_by(id_payroll_period=5).one()
            movimiento = (db.query(PayrollMovement).join(PayrollConcept, PayrollConcept.id_payroll_concept
                                                         == PayrollMovement.id_payroll_concept)
                          .filter(PayrollConcept.payroll_code == "SUELDO")
                          .filter(PayrollMovement.deletion_date.is_(None)).one())
            id_detalle, id_movimiento, id_concepto = (detalle.id_payroll_detail, movimiento.id_payroll_movement,
                                                      movimiento.id_payroll_concept)
        cerrar_periodo(5, 1)
        # 801 puede escribir todos los campos, asi que lo unico que lo detiene es
        # que el periodo este cerrado.
        h = self._headers(801)

        intentos = [
            self.client.put("/payroll_period/5", json={"payment_date": "2026-10-20"}, headers=h),
            self.client.delete("/payroll_period/5", headers=h),
            self.client.post("/payroll_detail/", json={"id_payroll_period": 5, "id_user": 72}, headers=h),
            self.client.put(f"/payroll_detail/{id_detalle}", json={"net_pay": 1}, headers=h),
            self.client.delete(f"/payroll_detail/{id_detalle}", headers=h),
            self.client.post("/payroll_movement/", json={"id_payroll_detail": id_detalle,
                                                         "id_payroll_concept": id_concepto, "amount": 10}, headers=h),
            self.client.put(f"/payroll_movement/{id_movimiento}", json={"amount": 1}, headers=h),
            self.client.delete(f"/payroll_movement/{id_movimiento}", headers=h),
            self.client.post("/payroll_period/5/calculate", headers=h),
        ]
        self.assertEqual([409] * len(intentos), [r.status_code for r in intentos])

    def test_el_estado_no_se_escribe_por_la_captura_generica(self):
        self._permisos()
        h = self._headers(801)
        self.assertEqual(200, self.client.put("/payroll_period/5", json={"period_state": "closed"},
                                              headers=h).status_code)
        self.assertEqual("open", self._estado())
        nuevo = self.client.post("/payroll_period/", json={
            "period_start": "2026-11-01", "period_end": "2026-11-15", "id_status": 1,
            "period_state": "closed"}, headers=h)
        self.assertEqual(201, nuevo.status_code)
        with transaction_context() as db:
            creado = db.get(PayrollPeriod, self.json(nuevo)["id_payroll_period"])
            self.assertEqual("open", creado.period_state)

    def test_solo_quien_administra_reabre_y_queda_registro(self):
        self._permisos()
        calcular_periodo(5, 1)
        self.assertEqual(200, self.client.post("/payroll_period/5/close", headers=self._headers(802)).status_code)

        self.assertEqual(403, self.client.post("/payroll_period/5/reopen", headers=self._headers(802)).status_code)
        respuesta = self.client.post("/payroll_period/5/reopen", headers=self._headers(801, id_user=9))

        self.assertEqual(200, respuesta.status_code)
        self.assertEqual("calculated", self.json(respuesta)["period_state"])
        self.assertEqual(9, self.json(respuesta)["reopened_by"])
        self.assertIsNotNone(self.json(respuesta)["reopened_at"])
        # Reabrir lo que no esta cerrado no tiene sentido.
        self.assertEqual(409, self.client.post("/payroll_period/5/reopen", headers=self._headers(801)).status_code)

    def test_el_resumen_no_recalcula(self):
        self._permisos()
        calcular_periodo(5, 1)
        with transaction_context() as db:
            vivos_antes = db.query(PayrollMovement).count()
        respuesta = self.client.get("/payroll_period/5/summary", headers=self._headers(802))
        self.assertEqual(1460.55, self.json(respuesta)["total_net_pay"])
        with transaction_context() as db:
            self.assertEqual(vivos_antes, db.query(PayrollMovement).count())

    def test_el_recibo_trae_los_datos_del_empleado(self):
        from app.services.payroll_calculation_service import datos_del_recibo
        calcular_periodo(5, 1)
        recibo = datos_del_recibo(5, 71)
        self.assertEqual("Ana", recibo["employee"])
        self.assertEqual(3, recibo["days_worked"])
        self.assertEqual([("Sueldo", 1500.0)], [(m["description"], m["amount"]) for m in recibo["earnings"]])
        self.assertEqual([("Cuota obrera IMSS", 39.45)], [(m["description"], m["amount"]) for m in recibo["deductions"]])
        self.assertEqual(1460.55, recibo["net_pay"])

    def test_no_hay_recibo_de_un_periodo_sin_calcular(self):
        self._permisos()
        respuesta = self.client.get("/payroll_period/5/receipt/71", headers=self._headers(802))
        self.assertEqual(409, respuesta.status_code)

    def test_el_recibo_sale_en_pdf(self):
        self._permisos()
        calcular_periodo(5, 1)
        respuesta = self.client.get("/payroll_period/5/receipt/71", headers=self._headers(802))
        self.assertEqual(200, respuesta.status_code)
        self.assertEqual("application/pdf", respuesta.mimetype)
        self.assertTrue(respuesta.data.startswith(b"%PDF"))


class TestIsrEImssEnElPeriodo(_ConPeriodoDePrueba):
    def test_un_sueldo_alto_paga_isr(self):
        with transaction_context() as db:
            db.get(User, 71).base_salary = Decimal("3000.00")
        ana = calcular_periodo(5, 1)["employees"][0]
        # 3 dias x 3,000 = 9,000 en quincena: 916.20 + (9,000 - 8,651.41) x 21.36% = 990.66.
        # Llevado a mes (18,240) pasa el limite del subsidio: subsidio 0.
        self.assertEqual(9000.0, ana["salary"])
        self.assertEqual(990.66, ana["isr_before_subsidy"])
        self.assertEqual(0.0, ana["employment_subsidy"])
        self.assertEqual(990.66, ana["isr"])

    def test_sin_cifras_oficiales_no_se_calcula(self):
        with transaction_context() as db:
            db.query(PayrollParameter).filter_by(parameter_key="uma_daily").delete()
        from app.utils.errors import AppError
        with self.assertRaises(AppError) as error:
            calcular_periodo(5, 1)
        self.assertEqual("errors.payroll_parameters_missing", error.exception.message_key)
        self.assertEqual(["uma_daily"], error.exception.meta["keys"])

    def test_sin_tarifa_del_anio_no_se_calcula(self):
        with transaction_context() as db:
            db.query(PayrollIsrBracket).delete()
        from app.utils.errors import AppError
        with self.assertRaises(AppError) as error:
            calcular_periodo(5, 1)
        self.assertEqual("errors.payroll_isr_table_missing", error.exception.message_key)

    def test_quien_gana_el_minimo_no_paga_imss(self):
        with transaction_context() as db:
            db.get(User, 71).base_salary = Decimal("315.04")
        ana = calcular_periodo(5, 1)["employees"][0]
        self.assertEqual(0.0, ana["imss"])


class TestMovimientosVigentes(_ConPeriodoDePrueba):
    def test_la_lista_no_muestra_los_movimientos_reemplazados(self):
        from app.services.payroll_movement_service import PayrollMovementService
        calcular_periodo(5, 1)
        calcular_periodo(5, 1)   # el recalculo deja los anteriores con borrado logico
        lista = PayrollMovementService.list(page=1, per_page=50, filters={})
        self.assertTrue(lista["items"])
        self.assertTrue(all(m["deletion_date"] is None for m in lista["items"]))
        with transaction_context() as db:
            vivos = db.query(PayrollMovement).filter(PayrollMovement.deletion_date.is_(None)).count()
            todos = db.query(PayrollMovement).count()
        self.assertEqual(vivos, lista["total"])
        self.assertGreater(todos, vivos)   # los reemplazados siguen en la base
