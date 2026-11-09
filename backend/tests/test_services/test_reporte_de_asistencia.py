"""Reporte de asistencia para RH (punto 8 de RH, 2026-11-04).

Mismo equipo que test_correcciones_de_checadas: Ana (71) trabaja L-V de 9 a 18
(tolerancia 10 min) y checa a las 8:00 y 17:00 los dias 1, 2 y 5 de octubre de
2026 (jueves, viernes y lunes). Del 1 al 11 de octubre: faltas el 6, 7, 8 y 9;
la del viernes 9 queda pegada al sabado 10 (descanso).
"""
from __future__ import annotations

import io
import zipfile
from datetime import date

from app.models import EntityPermission, Notification, PayrollParameter
from app.models.session import transaction_context
from app.routes.attendance_report import TITULOS
from app.services.overtime_service import confirmar, registrar
from app.services.reporte_de_asistencia import _h_mm, bitacora, reporte, xlsx
from app.utils.errors import AppError
from tests.test_services.test_correcciones_de_checadas import _ConChecadas
from tests.test_services.test_solicitudes_de_vacaciones import ANA, BETO, RH

DESDE, HASTA = "2026-10-01", "2026-10-11"


class TestReporte(_ConChecadas):
    def ana(self, datos=None):
        return next(f for f in (datos or reporte(DESDE, HASTA))["employees"] if f["id_user"] == ANA)

    def test_faltas_y_la_falta_pegada_al_fin_de_semana(self):
        datos = reporte(DESDE, HASTA)
        ana = self.ana(datos)
        self.assertEqual((0, 4, 1, 0), (ana["late"], ana["absences"], ana["absences_next_to_rest"], ana["manual_checks"]))
        self.assertEqual([("absences", "high"), ("absence_next_to_rest", "high")],
                         [(a["code"], a["level"]) for a in ana["alerts"]])
        self.assertEqual(ANA, datos["employees"][0]["id_user"])   # mas faltas, arriba
        self.assertEqual(1, datos["with_alerts"])

    def test_checadas_a_mano_retardos_y_quien_las_capturo(self):
        # Con tope de 2 al mes: Beto mueve dos entradas despues de la tolerancia y RH una tercera, como excepcion.
        with transaction_context() as db:
            db.add(PayrollParameter(parameter_key="attendance_correction_limit", value=2,
                                    valid_from=date(2026, 1, 1), created_by=1))
        for quien, dia in ((BETO, 1), (BETO, 2), (RH, 5)):
            r = self.corregir(quien, id_attendance_record=self.checada(dia, 8), new_time=f"2026-10-{dia:02d}T09:30",
                              reason=f"Llego tarde el {dia}")
            self.assertEqual(201, r.status_code)
        datos = reporte(DESDE, HASTA)
        ana = self.ana(datos)
        self.assertEqual((3, 90, 3, 1), (ana["late"], ana["late_minutes"], ana["manual_checks"], ana["manual_exceptions"]))
        self.assertEqual({"late", "manual", "absences", "absence_next_to_rest"}, {a["code"] for a in ana["alerts"]})
        self.assertEqual([("2026-10-01", "Beto", "Llego tarde el 1"), ("2026-10-05", "Rocio RH", "Llego tarde el 5")],
                         [(m["date"], m["by"], m["reason"]) for m in ana["manual_reasons"]][::2])
        self.assertEqual([("Beto", 2, False), ("Rocio RH", 1, False)],
                         [(s["full_name"], s["manual_checks"], s["alert"]) for s in datos["supervisors"]])

    def test_los_limites_los_cambia_la_empresa_y_cero_apaga_la_alerta(self):
        with transaction_context() as db:
            for clave, valor in (("report_alert_absences", 0), ("report_alert_supervisor_manual", 1)):
                db.add(PayrollParameter(parameter_key=clave, value=valor, valid_from=date(2026, 1, 1), created_by=1))
        self.corregir(BETO, id_attendance_record=self.checada(1, 8), new_time="2026-10-01T08:30")
        datos = reporte(DESDE, HASTA)
        self.assertEqual(["absence_next_to_rest"], [a["code"] for a in self.ana(datos)["alerts"]])
        self.assertEqual((0, 1), (datos["limits"]["report_alert_absences"], datos["limits"]["report_alert_supervisor_manual"]))
        self.assertTrue(datos["supervisors"][0]["alert"])
        # El orden no depende de que alerta este prendida: con 4 faltas Ana sigue arriba.
        self.assertEqual(ANA, datos["employees"][0]["id_user"])

    def test_horas_extra_confirmadas_y_pendientes_de_rh(self):
        pendiente = registrar({"id_user": BETO, "id_permission": 2}, {"id_user": ANA, "work_date": "2026-10-02", "minutes": 60})
        registrar({"id_user": BETO, "id_permission": 2}, {"id_user": ANA, "work_date": "2026-10-05", "minutes": 30})
        confirmar({"id_user": RH}, pendiente["id_overtime"], True)
        ana = self.ana()
        self.assertEqual((60, 30), (ana["overtime_minutes"], ana["overtime_pending_minutes"]))

    def test_bitacora_de_correcciones_para_rh(self):
        """Sin limite (2026-11-04): RH ve cada movimiento y quien lo hizo, y filtra por supervisor."""
        for quien, dia in ((BETO, 1), (BETO, 2), (RH, 5)):
            self.corregir(quien, id_attendance_record=self.checada(dia, 8), new_time=f"2026-10-{dia:02d}T09:30",
                          reason=f"Motivo {dia}")
        self.corregir(BETO, id_user=ANA, new_time="2026-10-06T18:00", reason="Agrego salida")
        todo = bitacora(DESDE, HASTA)
        self.assertEqual(4, len(todo["corrections"]))
        self.assertEqual(["Beto", "Rocio RH"], [s["full_name"] for s in todo["supervisors"]])
        primera = next(c for c in todo["corrections"] if c["date"] == "2026-10-01")
        self.assertEqual(("Ana", "08:00", "09:30", "Motivo 1", "Beto", False),
                         (primera["employee"], primera["previous_time"], primera["new_time"], primera["reason"],
                          primera["by"], primera["added"]))
        agregada = next(c for c in todo["corrections"] if c["date"] == "2026-10-06")
        self.assertEqual((None, "18:00", True), (agregada["previous_time"], agregada["new_time"], agregada["added"]))
        solo_beto = bitacora(DESDE, HASTA, BETO)
        self.assertEqual({"Beto"}, {c["by"] for c in solo_beto["corrections"]})
        self.assertEqual(3, len(solo_beto["corrections"]))
        self.assertEqual(2, len(solo_beto["supervisors"]))     # el filtro sigue ofreciendo a todos
        with self.assertRaises(AppError):
            bitacora("2026-01-01", "2027-06-01")

    def test_rango_invalido(self):
        for desde, hasta in (("2026-10-11", "2026-10-01"), ("2026-10-01", "2026-11-01"), ("ayer", "2026-10-01")):
            with self.subTest(desde=desde), self.assertRaises(AppError) as error:
                reporte(desde, hasta)
            self.assertEqual("errors.invalid_field", error.exception.message_key)

    def test_horas_como_en_pantalla(self):
        self.assertEqual(("2:00", "0:30", "0:00"), (_h_mm(120), _h_mm(30), _h_mm(None)))

    def test_excel(self):
        contenido, nombre = xlsx(DESDE, HASTA, TITULOS)
        self.assertEqual("asistencia_2026-10-01_2026-10-11.xlsx", nombre)
        hoja = zipfile.ZipFile(io.BytesIO(contenido)).read("xl/worksheets/sheet1.xml").decode()
        for texto in ("Ana", "Faltas repetidas", "Falta junto a descanso o festivo", "Retardos"):
            self.assertIn(texto, hoja)
        # Horas como en pantalla, columnas con ancho y acentos (revision del tester, 5-nov).
        for texto in ("<t>0:00</t>", "(h:mm)", "<cols>", "Días de permiso"):
            self.assertIn(texto, hoja)


class TestRutas(_ConChecadas):
    """Lo controla la capacidad attendance_report del Gestor."""

    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.add(EntityPermission(id_permission=962, entity_name="attendance_report", scope_create=0,
                                    scope_read=4, scope_update=0, scope_delete=0, created_by=1))

    def test_con_la_capacidad_y_sin_ella(self):
        url = f"/attendance_report/?start={DESDE}&end={HASTA}"
        self.assertEqual(200, self.client.get(url, headers=self.h(RH, 962)).status_code)
        # RH edita checadas pero sin la capacidad del reporte no lo ve.
        self.assertEqual(403, self.client.get(url, headers=self.h(RH, 961)).status_code)
        r = self.client.get(f"/attendance_report/xlsx?start={DESDE}&end={HASTA}", headers=self.h(RH, 962))
        self.assertEqual((200, "attachment"), (r.status_code, r.headers["Content-Disposition"].split(";")[0]))
        self.assertEqual(200, self.client.get(f"/attendance_report/corrections?start={DESDE}&end={HASTA}",
                                              headers=self.h(RH, 962)).status_code)
        self.assertEqual(403, self.client.get(f"/attendance_report/corrections?start={DESDE}&end={HASTA}",
                                              headers=self.h(RH, 961)).status_code)


class TestTipoDeIncidente(_ConChecadas):
    """Tipo de incidente de cada correccion (respuestas de RH, 2026-11-04)."""

    def test_se_guarda_se_cuenta_y_la_falla_del_checador_no_alerta(self):
        for dia, tipo in ((1, "device_failure"), (2, "device_failure"), (5, "forgot")):
            r = self.corregir(BETO, id_attendance_record=self.checada(dia, 8), new_time=f"2026-10-{dia:02d}T08:05",
                              incident_kind=tipo)
            self.assertEqual((201, tipo), (r.status_code, self.json(r)["incident_kind"]))
        ana = next(f for f in reporte(DESDE, HASTA)["employees"] if f["id_user"] == ANA)
        self.assertEqual((3, {"device_failure": 2, "forgot": 1}), (ana["manual_checks"], ana["manual_by_kind"]))
        self.assertNotIn("manual", {a["code"] for a in ana["alerts"]})       # solo 1 que no fue falla del checador
        self.assertEqual("device_failure", bitacora(DESDE, HASTA)["corrections"][-1]["kind"])

    def test_un_tipo_que_no_existe(self):
        r = self.corregir(BETO, id_attendance_record=self.checada(1, 8), new_time="2026-10-01T08:05", incident_kind="otro")
        self.assertEqual(400, r.status_code)


class TestAvisosARh(_ConChecadas):
    """Si se cumple un patron, se le avisa a RH (quien tiene el reporte en el Gestor), sin repetir."""

    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.add(EntityPermission(id_permission=961, entity_name="attendance_report", scope_create=0,
                                    scope_read=4, scope_update=0, scope_delete=0, created_by=1))

    def avisos(self, tipo):
        with transaction_context() as db:
            return [(n.id_user_recipient, n.target_entity, n.target_id, n.title, n.message, n.metadata_data)
                    for n in db.query(Notification).filter(Notification.notification_type == tipo)]

    def test_avisa_una_vez_y_luego_solo_lo_nuevo(self):
        from app.services.reporte_de_asistencia import avisar_alertas_de_asistencia
        self.assertEqual(1, avisar_alertas_de_asistencia(date(2026, 10, 11)))
        [(quien, destino, id_ana, titulo, mensaje, meta)] = self.avisos("attendance_alert")
        self.assertEqual((RH, "attendance_report", ANA, "Alerta de asistencia: Ana"), (quien, destino, id_ana, titulo))
        self.assertIn("faltas repetidas (4)", mensaje)
        self.assertEqual(["absence_next_to_rest", "absences"], meta["codes"])
        self.assertEqual(0, avisar_alertas_de_asistencia(date(2026, 10, 11)))   # nada nuevo: no repite
        # Un patron nuevo en la misma quincena: se avisa solo ese.
        for dia in (1, 2, 5):
            self.corregir(BETO, id_attendance_record=self.checada(dia, 8), new_time=f"2026-10-{dia:02d}T09:30")
        self.assertEqual(1, avisar_alertas_de_asistencia(date(2026, 10, 11)))
        self.assertEqual(["late", "manual"], self.avisos("attendance_alert")[-1][5]["codes"])

    def test_resumen_quincenal_por_omision_y_semanal_si_se_elige(self):
        from app.services.reporte_de_asistencia import enviar_resumen_de_asistencia
        self.assertEqual(0, enviar_resumen_de_asistencia(date(2026, 10, 15)))   # no es dia 1 ni 16
        self.assertEqual(1, enviar_resumen_de_asistencia(date(2026, 10, 16)))
        self.assertEqual(0, enviar_resumen_de_asistencia(date(2026, 10, 16)))   # ya se mando
        [(quien, _, _, titulo, mensaje, meta)] = self.avisos("attendance_summary")
        self.assertEqual((RH, "Resumen de asistencia de la quincena", "2026-10-01"), (quien, titulo, meta["start"]))
        self.assertTrue(mensaje.startswith("Del 01/10 al 15/10: 1 de"))
        with transaction_context() as db:
            db.add(PayrollParameter(parameter_key="report_summary_frequency", value=1, valid_from=date(2026, 1, 1),
                                    created_by=1))
        self.assertEqual(0, enviar_resumen_de_asistencia(date(2026, 10, 16)))   # semanal: solo los lunes
        self.assertEqual(1, enviar_resumen_de_asistencia(date(2026, 10, 12)))   # lunes: semana del 5 al 11
