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

from app.models import EntityPermission, PayrollParameter
from app.models.session import transaction_context
from app.routes.attendance_report import TITULOS
from app.services.overtime_service import confirmar, registrar
from app.services.reporte_de_asistencia import bitacora, reporte, xlsx
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
        self.assertEqual(ANA, datos["employees"][0]["id_user"])   # quien tiene alertas va primero
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

    def test_excel(self):
        contenido, nombre = xlsx(DESDE, HASTA, TITULOS)
        self.assertEqual("asistencia_2026-10-01_2026-10-11.xlsx", nombre)
        hoja = zipfile.ZipFile(io.BytesIO(contenido)).read("xl/worksheets/sheet1.xml").decode()
        for texto in ("Ana", "Faltas repetidas", "Falta junto a descanso o festivo", "Retardos"):
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
