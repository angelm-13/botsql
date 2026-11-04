"""Horas extra (Etapa C; decisiones de RH 2026-10-30).

Mismo equipo que test_solicitudes_de_vacaciones: Ana (71) gana 500 diarios y
trabaja L-V de 9 a 18 con 60 minutos de comida (jornada de 8 h: la hora vale
62.50); su jefe es Beto (80) y Rocio (82) es RH. Periodo 5 = 1 al 15 de octubre.

Cuentas a mano:
  Autorizadas 3 h el martes 6 pero checo salida a las 20:30: se pagan 2.5 h dobles
  = 2.5 x 125 = 312.50. Exento: la mitad de lo doble (156.25), bajo el tope de
  5 UMA (586.55): grava 156.25.
  12 h en la semana del 5 al 11 (4 h el 6, 7 y 8): 9 dobles = 1,125.00 y 3 triples =
  562.50; total 1,687.50. Exento: la mitad de lo doble, 562.50 (bajo 586.55);
  grava 1,125.00.
  Con 30 minutos de comida la jornada es de 8.5 h: la hora vale 58.82 y 1 h doble 117.65.
  Ganando el salario minimo (315.04) lo doble no grava.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from app.models import AttendanceRecord, EntityPermission, Overtime, PayrollParameter, PayrollPeriod, User, WorkSchedule
from app.models.session import transaction_context
from app.services.overtime_service import del_rango, registrar
from app.services.payroll_calculation_service import calcular_periodo, cerrar_periodo, reabrir_periodo
from app.services.overtime_service import confirmar
from app.utils.errors import AppError
from tests.test_services.test_solicitudes_de_vacaciones import ANA, BETO, RH, _ConEquipo

JEFE = {"id_user": BETO, "id_permission": 2}
RRHH = {"id_user": RH, "id_permission": 961}


class _ConHorasExtra(_ConEquipo):
    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.add(EntityPermission(id_permission=961, entity_name="attendance_record", scope_create=4,
                                    scope_read=4, scope_update=4, scope_delete=4, created_by=1))

    def checa(self, dia, salida, entrada=(9, 0)):
        with transaction_context() as db:
            for n, (h, m) in enumerate((entrada, salida)):
                db.add(AttendanceRecord(id_user=ANA, employee_no="71", check_time=datetime(2026, 10, dia, h, m),
                                        source="kronos", source_ref=f"he:{dia}:{n}", created_by=1))

    def autoriza(self, dia, minutos, quien=JEFE, confirma_rh=True, **extra):
        """Lo registra el jefe y, como en la operacion normal, RH lo confirma (jefe y luego RH)."""
        hecho = registrar(quien, {"id_user": ANA, "work_date": f"2026-10-{dia:02d}", "minutes": minutos, **extra})
        if confirma_rh and hecho["approval_status"] == "pending_hr":
            hecho = confirmar(RRHH, hecho["id_overtime"], True)
        return hecho

    def ana(self, periodo=5):
        return next(e for e in calcular_periodo(periodo, 1)["employees"] if e["id_user"] == ANA)


class TestVerificar(_ConHorasExtra):
    def test_se_paga_lo_checado_con_tope_en_lo_autorizado(self):
        self.checa(6, (20, 30))
        self.autoriza(6, 180)
        fila = del_rango(JEFE, "2026-10-01", "2026-10-15")["overtime"][0]
        self.assertEqual((180, 150, 150, "partial"),
                         (fila["minutes"], fila["checked_minutes"], fila["payable_minutes"], fila["status"]))
        ana = self.ana()
        self.assertEqual((2.5, 0.0, 312.50, 156.25), (ana["overtime_double_hours"], ana["overtime_triple_hours"],
                                                      ana["overtime_pay"], ana["overtime_taxable"]))

    def test_si_no_se_quedo_no_se_paga(self):
        self.autoriza(6, 120)
        self.assertEqual("not_worked", del_rango(JEFE, "2026-10-01", "2026-10-15")["overtime"][0]["status"])
        self.assertEqual(0.0, self.ana()["overtime_pay"])

    def test_el_tiempo_no_autorizado_se_ve_y_se_aprueba(self):
        self.checa(6, (20, 30))
        datos = del_rango(JEFE, "2026-10-01", "2026-10-15")
        self.assertEqual([("2026-10-06", 150)], [(u["work_date"], u["minutes"]) for u in datos["unauthorized"]])
        self.assertEqual(0.0, self.ana()["overtime_pay"])            # sin aprobar no se paga
        self.autoriza(6, 150, origin="detected")
        datos = del_rango(JEFE, "2026-10-01", "2026-10-15")
        self.assertEqual(([], "verified"), (datos["unauthorized"], datos["overtime"][0]["status"]))

    def test_dentro_de_la_tolerancia_no_es_tiempo_no_autorizado(self):
        self.checa(6, (18, 15))
        self.assertEqual([], del_rango(JEFE, "2026-10-01", "2026-10-15")["unauthorized"])


class TestCuanto(_ConHorasExtra):
    def test_mas_de_9_horas_en_la_semana_son_triples(self):
        for dia in (6, 7, 8):
            self.checa(dia, (22, 0))
            self.autoriza(dia, 240)
        ana = self.ana()
        self.assertEqual((9.0, 3.0, 1687.50, 1125.00), (ana["overtime_double_hours"], ana["overtime_triple_hours"],
                                                        ana["overtime_pay"], ana["overtime_taxable"]))

    def test_por_omision_la_hora_es_el_diario_entre_8_aunque_su_jornada_sea_otra(self):
        """Decision de RH (2026-11-04): base de 8 horas, configurable."""
        with transaction_context() as db:
            for h in db.query(WorkSchedule):
                h.meal_minutes = 30           # su jornada seria de 8.5 h
        self.checa(6, (19, 0))
        self.autoriza(6, 60)
        self.assertEqual(125.0, self.ana()["overtime_pay"])          # 500 / 8 x 2

    def test_la_empresa_puede_cambiar_las_8_horas(self):
        with transaction_context() as db:
            db.add(PayrollParameter(parameter_key="overtime_day_hours", value=10, valid_from=date(2026, 1, 1),
                                    created_by=1))
        self.checa(6, (19, 0))
        self.autoriza(6, 60)
        self.assertEqual(100.0, self.ana()["overtime_pay"])          # 500 / 10 x 2

    def test_con_la_opcion_la_comida_del_horario_cambia_el_precio_de_la_hora(self):
        with transaction_context() as db:
            for h in db.query(WorkSchedule):
                h.meal_minutes = 30
            db.add(PayrollParameter(parameter_key="overtime_hours_from_schedule", value=1,
                                    valid_from=date(2026, 1, 1), created_by=1))
        self.checa(6, (19, 0))
        self.autoriza(6, 60)
        self.assertEqual(117.65, self.ana()["overtime_pay"])         # 500 / 8.5 x 2

    def test_con_salario_minimo_lo_doble_no_grava(self):
        with transaction_context() as db:
            db.get(User, ANA).base_salary = Decimal("315.04")
        self.checa(6, (20, 0))
        self.autoriza(6, 120)
        ana = self.ana()
        self.assertEqual((157.52, 0.0), (ana["overtime_pay"], ana["overtime_taxable"]))   # 315.04 / 8 x 2 x 2 h

    def test_el_tiempo_libre_no_se_paga_y_pide_comentario(self):
        self.checa(6, (20, 0))
        with self.assertRaises(AppError):
            self.autoriza(6, 120, settlement="compensate")
        self.autoriza(6, 120, settlement="compensate", notes="Sale temprano el viernes")
        self.assertEqual(0.0, self.ana()["overtime_pay"])


class TestQuienYCuando(_ConHorasExtra):
    def test_la_captura_a_mano_es_solo_de_rh_y_con_motivo(self):
        with self.assertRaises(AppError) as error:
            self.autoriza(6, 120, origin="manual", notes="Inventario")
        self.assertEqual(403, error.exception.status_code)
        with self.assertRaises(AppError):
            self.autoriza(6, 120, quien=RRHH, origin="manual")
        self.autoriza(6, 120, quien=RRHH, origin="manual", notes="Inventario, no checo")
        self.assertEqual(250.0, self.ana()["overtime_pay"])           # 2 h dobles sin checadas

    def test_el_empleado_no_registra_las_suyas(self):
        with self.assertRaises(AppError) as error:
            self.autoriza(6, 60, quien={"id_user": ANA, "id_permission": 2})
        self.assertEqual(403, error.exception.status_code)

    def test_aprobadas_despues_de_cerrar_se_pagan_en_el_siguiente_y_una_sola_vez(self):
        self.checa(6, (20, 0))
        self.ana()
        cerrar_periodo(5, 1, confirmar_pendientes=True)
        with transaction_context() as db:
            db.add(PayrollPeriod(id_payroll_period=6, period_start=date(2026, 10, 16), period_end=date(2026, 10, 31),
                                 payment_date=date(2026, 10, 31), id_status=1, created_by=1))
        self.autoriza(6, 120)
        self.assertEqual(250.0, self.ana(6)["overtime_pay"])
        cerrar_periodo(6, 1, confirmar_pendientes=True)
        with transaction_context() as db:
            self.assertEqual([6], [o.id_payroll_period for o in db.query(Overtime)])
        reabrir_periodo(6, 1)
        with transaction_context() as db:
            self.assertEqual([None], [o.id_payroll_period for o in db.query(Overtime)])


class TestJefeYLuegoRh(_ConHorasExtra):
    """Lo que registra el jefe queda pendiente de RH y no se paga hasta que RH lo confirma (2026-11-04)."""

    def test_pendiente_no_se_paga_confirmado_si_y_rechazado_no(self):
        self.checa(6, (20, 0))
        hecho = self.autoriza(6, 120, confirma_rh=False)
        self.assertEqual("pending_hr", hecho["approval_status"])
        self.assertEqual(0.0, self.ana()["overtime_pay"])
        self.assertEqual("approved", confirmar(RRHH, hecho["id_overtime"], True)["approval_status"])
        self.assertEqual(250.0, self.ana()["overtime_pay"])
        otro = self.autoriza(7, 60, confirma_rh=False)
        self.assertEqual("rejected", confirmar(RRHH, otro["id_overtime"], False, "no se pidio")["approval_status"])
        with self.assertRaises(AppError) as error:
            confirmar(RRHH, otro["id_overtime"], True)
        self.assertEqual("errors.overtime_not_pending", error.exception.message_key)

    def test_lo_que_registra_rh_ya_queda_confirmado_y_solo_rh_confirma(self):
        self.assertEqual("approved", self.autoriza(6, 60, quien=RRHH, confirma_rh=False)["approval_status"])
        hecho = self.autoriza(7, 60, confirma_rh=False)
        r = self.client.post(f"/overtime/{hecho['id_overtime']}/review", headers=self.h(BETO, 2), json={"approve": True})
        self.assertEqual(403, r.status_code)
        r = self.client.post(f"/overtime/{hecho['id_overtime']}/review", headers=self.h(RH, 961), json={"approve": True})
        self.assertEqual((200, "approved"), (r.status_code, self.json(r)["approval_status"]))
