"""Correcciones de checadas con limite por mes (revision contable, 2026-10-28).

Mismo equipo que test_solicitudes_de_vacaciones: Ana (71) con su jefe Beto (80),
Carla (81) de otro jefe y Rocio (82) de RH. Ana trabaja L-V de 9 a 18 y checa
a las 8:00 y a las 17:00 los dias 1, 2 y 5 de octubre de 2026; el periodo 5 (1 al
15) le paga 7 dias (15 menos 8 faltas).

Reglas: corrige su jefe o RH, nunca el propio empleado; cada hora corregida o
agregada cuenta 1 y el limite es 2 por mes (lo cambia la empresa); despues del
limite solo RH, como excepcion. Un dia con una sola checada queda pendiente de
justificar: no se paga y al cerrar la nomina se avisa.
"""
from __future__ import annotations

from datetime import date, datetime

from app.models import AttendanceRecord, EntityPermission, PayrollParameter
from app.models.session import transaction_context
from app.services.payroll_calculation_service import calcular_periodo, cerrar_periodo
from app.utils.errors import AppError
from tests.test_services.test_solicitudes_de_vacaciones import ANA, BETO, CARLA, RH, _ConEquipo


class _ConChecadas(_ConEquipo):
    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.add(EntityPermission(id_permission=961, entity_name="attendance_record", scope_create=4,
                                    scope_read=4, scope_update=4, scope_delete=4, created_by=1))

    def checada(self, dia, hora):
        with transaction_context() as db:
            return db.query(AttendanceRecord).filter(
                AttendanceRecord.id_user == ANA,
                AttendanceRecord.check_time == datetime(2026, 10, dia, hora)).one().id_attendance_record

    def olvidar_salida(self, dia=5):
        with transaction_context() as db:
            db.get(AttendanceRecord, self.checada(dia, 17)).deletion_date = datetime(2026, 10, 20)

    def corregir(self, quien, **cuerpo):
        cuerpo.setdefault("reason", "Se le olvido checar")
        return self.client.post("/attendance_correction/", headers=self.h(quien), json=cuerpo)

    def contador(self, quien, mes="2026-10"):
        return self.client.get(f"/attendance_correction/?id_user={ANA}&month={mes}", headers=self.h(quien))

    def ana(self):
        return calcular_periodo(5, 1)["employees"][0]


class TestDiaPendiente(_ConChecadas):
    def test_una_sola_checada_queda_pendiente_y_no_se_paga(self):
        self.olvidar_salida()
        ana = self.ana()
        self.assertEqual((6, 1, 8), (ana["days_worked"], ana["pending_justification"], ana["absences"]))

    def test_cerrar_avisa_y_solo_cierra_si_rh_confirma(self):
        self.olvidar_salida()
        self.ana()
        with self.assertRaises(AppError) as error:
            cerrar_periodo(5, 1)
        self.assertEqual("errors.payroll_period_pending_justification", error.exception.message_key)
        self.assertEqual([{"id_user": ANA, "full_name": "Ana", "dates": ["2026-10-05"]}],
                         error.exception.meta["employees"])
        self.assertEqual("closed", cerrar_periodo(5, 1, confirmar_pendientes=True)["period_state"])


class TestCorregir(_ConChecadas):
    def test_el_jefe_corrige_la_misma_checada_y_queda_el_historial(self):
        r = self.corregir(BETO, id_attendance_record=self.checada(1, 8), new_time="2026-10-01T08:55")
        self.assertEqual(201, r.status_code)
        datos = self.json(r)
        self.assertEqual(("2026-10-01T08:00:00", "2026-10-01T08:55:00", False, 1, None),   # sin limite: no hay restantes
                         (datos["previous_time"], datos["new_time"], datos["is_exception"], datos["used"],
                          datos["remaining"]))
        with transaction_context() as db:
            self.assertEqual(datetime(2026, 10, 1, 8, 55), db.get(AttendanceRecord, datos["id_attendance_record"]).check_time)

    def test_agregar_la_salida_que_faltaba_cuenta_y_el_dia_ya_se_paga(self):
        self.olvidar_salida()
        r = self.corregir(BETO, id_user=ANA, new_time="2026-10-05T18:00")
        self.assertEqual((201, None), (r.status_code, self.json(r)["previous_time"]))
        ana = self.ana()
        self.assertEqual((7, 0), (ana["days_worked"], ana["pending_justification"]))
        self.assertEqual(1, self.json(self.contador(BETO))["used"])

    def test_solo_cambia_la_hora_no_el_dia(self):
        r = self.corregir(BETO, id_attendance_record=self.checada(1, 8), new_time="2026-10-02T08:00")
        self.assertEqual(400, r.status_code)

    def test_el_motivo_es_obligatorio(self):
        r = self.corregir(BETO, id_attendance_record=self.checada(1, 8), new_time="2026-10-01T08:30", reason=" ")
        self.assertEqual(400, r.status_code)


class TestLimite(_ConChecadas):
    def con_limite(self, valor):
        with transaction_context() as db:
            db.add(PayrollParameter(parameter_key="attendance_correction_limit", value=valor,
                                    valid_from=date(2026, 1, 1), created_by=1))

    def test_por_omision_el_supervisor_corrige_sin_limite(self):
        """Decision de RH (2026-11-04): sin tope; RH vigila con la bitacora."""
        for dia, hora in ((1, 8), (1, 17), (2, 8), (2, 17), (5, 8)):
            r = self.corregir(BETO, id_attendance_record=self.checada(dia, hora), new_time=f"2026-10-{dia:02d}T{hora:02d}:05")
            self.assertEqual((201, False), (r.status_code, self.json(r)["is_exception"]))
        self.assertEqual((0, 5, None), (self.json(self.contador(BETO))["limit"], self.json(self.contador(BETO))["used"],
                                        self.json(self.contador(BETO))["remaining"]))

    def test_dos_al_mes_y_despues_solo_rh_como_excepcion(self):
        self.con_limite(2)
        self.assertEqual(201, self.corregir(BETO, id_attendance_record=self.checada(1, 8),
                                            new_time="2026-10-01T09:00").status_code)
        self.assertEqual(201, self.corregir(BETO, id_attendance_record=self.checada(1, 17),
                                            new_time="2026-10-01T18:00").status_code)
        r = self.corregir(BETO, id_attendance_record=self.checada(2, 8), new_time="2026-10-02T09:00")
        self.assertEqual(409, r.status_code)
        self.assertEqual("errors.attendance_correction_limit_reached", self.json(r)["error_key"])
        r = self.corregir(RH, id_attendance_record=self.checada(2, 8), new_time="2026-10-02T09:00",
                          reason="Se cayo el checador")
        self.assertEqual((201, True), (r.status_code, self.json(r)["is_exception"]))
        self.assertEqual((2, 3, 0), (self.json(self.contador(RH))["limit"], self.json(self.contador(RH))["used"],
                                     self.json(self.contador(RH))["remaining"]))

    def test_el_limite_lo_cambia_la_empresa(self):
        with transaction_context() as db:
            db.add(PayrollParameter(parameter_key="attendance_correction_limit", value=1,
                                    valid_from=date(2026, 1, 1), created_by=1))
        self.corregir(BETO, id_attendance_record=self.checada(1, 8), new_time="2026-10-01T09:00")
        self.assertEqual(409, self.corregir(BETO, id_attendance_record=self.checada(1, 17),
                                            new_time="2026-10-01T18:00").status_code)

    def test_cuenta_el_mes_de_la_checada(self):
        self.corregir(BETO, id_attendance_record=self.checada(1, 8), new_time="2026-10-01T09:00")
        self.assertEqual(0, self.json(self.contador(BETO, "2026-11"))["used"])


class TestQuienCorrige(_ConChecadas):
    def test_ni_el_propio_empleado_ni_otro_jefe(self):
        for quien in (ANA, CARLA):
            self.assertEqual(403, self.corregir(quien, id_attendance_record=self.checada(1, 8),
                                                new_time="2026-10-01T08:30").status_code)

    def test_el_empleado_no_ve_su_contador(self):
        self.assertEqual(403, self.contador(ANA).status_code)
        self.assertEqual(200, self.contador(BETO).status_code)

    def test_no_se_corrige_en_un_periodo_cerrado(self):
        self.ana()
        cerrar_periodo(5, 1)
        r = self.corregir(RH, id_attendance_record=self.checada(1, 8), new_time="2026-10-01T08:30")
        self.assertEqual(("errors.payroll_period_closed", 409), (self.json(r)["error_key"], r.status_code))
