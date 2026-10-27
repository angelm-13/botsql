"""Checadas guardadas: importar desde Kronos y leer lo guardado.

Antes la pantalla de Asistencias solo leia el checador en vivo y no guardaba
nada. Estas pruebas cubren lo nuevo: que importar guarde cada checada una sola
vez (aunque se importe dos veces el mismo rango), que la hora se guarde como
hora del negocio y que el reporte leido de la base salga igual que el del
checador.
"""
from __future__ import annotations

from datetime import date, datetime
from unittest.mock import patch

import jwt

from app.models import AttendanceRecord
from app.models.entity_permission import EntityPermission
from app.models.session import transaction_context
from app.services.attendance_record_service import (
    checadas_en_rango,
    evento_kronos_a_registro,
    importar_eventos_kronos,
)
from app.utils.auth import SECRET_KEY
from tests.conftest import BackendTestCase

EQUIPO = {"deviceUrl": "https://checador.local", "username": "admin", "password": "secreto"}

EVENTOS = [
    {"serialNo": 11, "employeeNoString": "7", "name": "Ana", "time": "2026-10-15T08:02:00-06:00",
     "doorNo": 1, "currentVerifyMode": "fingerPrint"},
    {"serialNo": 12, "employeeNoString": "7", "name": "Ana", "time": "2026-10-15T17:10:00-06:00",
     "doorNo": 1, "currentVerifyMode": "fingerPrint"},
    # Un evento de puerta sin persona: no es una checada.
    {"serialNo": 13, "time": "2026-10-15T09:00:00-06:00", "doorNo": 1},
]


class TestEventoKronosARegistro(BackendTestCase):
    def test_la_hora_se_guarda_como_hora_del_negocio(self):
        fila = evento_kronos_a_registro(
            {"serialNo": 5, "employeeNoString": "7", "time": "2026-10-15T14:02:00Z"}, "checador.local")
        # 14:02 UTC son las 08:02 en Ciudad de Mexico.
        self.assertEqual(datetime(2026, 10, 15, 8, 2), fila["check_time"])
        self.assertIsNone(fila["check_time"].tzinfo)

    def test_la_referencia_es_el_equipo_y_el_numero_de_serie(self):
        fila = evento_kronos_a_registro(EVENTOS[0], "checador.local")
        self.assertEqual("checador.local:11", fila["source_ref"])
        self.assertEqual("kronos", fila["source"])

    def test_sin_numero_de_serie_se_reconoce_por_quien_y_cuando(self):
        fila = evento_kronos_a_registro(
            {"employeeNoString": "7", "time": "2026-10-15T08:02:00-06:00"}, "checador.local")
        self.assertEqual("checador.local:7:2026-10-15T08:02:00", fila["source_ref"])

    def test_un_evento_sin_empleado_o_sin_hora_se_descarta(self):
        self.assertIsNone(evento_kronos_a_registro(EVENTOS[2], "checador.local"))
        self.assertIsNone(evento_kronos_a_registro({"employeeNoString": "7", "time": "ayer"}, "x"))


class TestImportarEventosKronos(BackendTestCase):
    def test_importar_dos_veces_no_duplica(self):
        primera = importar_eventos_kronos(EVENTOS, EQUIPO["deviceUrl"], 1)
        segunda = importar_eventos_kronos(EVENTOS, EQUIPO["deviceUrl"], 1)

        self.assertEqual({"received": 3, "saved": 2, "already_saved": 0, "skipped": 1}, primera)
        self.assertEqual({"received": 3, "saved": 0, "already_saved": 2, "skipped": 1}, segunda)
        with transaction_context() as db:
            self.assertEqual(2, db.query(AttendanceRecord).count())

    def test_el_nombre_sale_del_directorio_cuando_el_evento_no_lo_trae(self):
        evento = {"serialNo": 1, "employeeNoString": "9", "time": "2026-10-15T08:00:00-06:00"}
        importar_eventos_kronos([evento], EQUIPO["deviceUrl"], 1, [{"employeeNo": "9", "name": "Luis"}])
        fila = checadas_en_rango(date(2026, 10, 15), date(2026, 10, 15))[0]
        self.assertEqual("Luis", fila.employee_name)

    def test_el_rango_incluye_ambos_dias(self):
        importar_eventos_kronos(EVENTOS, EQUIPO["deviceUrl"], 1)
        self.assertEqual(2, len(checadas_en_rango(date(2026, 10, 15), date(2026, 10, 15))))
        self.assertEqual(0, len(checadas_en_rango(date(2026, 10, 16), date(2026, 10, 16))))


class TestRutasDeChecadasGuardadas(BackendTestCase):
    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            db.add_all([
                # Rol que administra checadas.
                EntityPermission(id_permission=501, entity_name="attendance_record",
                                  scope_create=4, scope_read=4, scope_update=4, scope_delete=4, created_by=1),
                # Rol que solo las consulta.
                EntityPermission(id_permission=502, entity_name="attendance_record",
                                  scope_create=0, scope_read=4, scope_update=0, scope_delete=0, created_by=1),
            ])

    def _headers(self, id_permission):
        token = jwt.encode({"id_user": 41, "id_permission": id_permission}, SECRET_KEY, algorithm="HS256")
        return {"Authorization": f"Bearer {token}"}

    @patch("app.routes.kronos.KronosService")
    def test_importar_guarda_lo_que_contesta_el_checador(self, servicio):
        servicio.return_value.fetch_attendance.return_value = EVENTOS
        servicio.return_value.fetch_people.return_value = []
        cuerpo = {**EQUIPO, "startTime": "2026-10-15T00:00:00-06:00", "endTime": "2026-10-15T23:59:59-06:00"}

        respuesta = self.client.post("/kronos/attendance/import", json=cuerpo, headers=self._headers(501))

        self.assertEqual(200, respuesta.status_code)
        self.assertEqual(2, self.json(respuesta)["saved"])
        with transaction_context() as db:
            self.assertEqual(41, db.query(AttendanceRecord).first().created_by)

    @patch("app.routes.kronos.KronosService")
    def test_quien_solo_consulta_no_puede_importar(self, servicio):
        cuerpo = {**EQUIPO, "startTime": "2026-10-15T00:00:00-06:00", "endTime": "2026-10-15T23:59:59-06:00"}
        respuesta = self.client.post("/kronos/attendance/import", json=cuerpo, headers=self._headers(502))
        self.assertEqual(403, respuesta.status_code)
        servicio.assert_not_called()

    def test_lo_guardado_da_el_mismo_reporte_que_el_checador(self):
        importar_eventos_kronos(EVENTOS, EQUIPO["deviceUrl"], 1)

        respuesta = self.client.get(
            "/kronos/attendance/saved?startDate=2026-10-15&endDate=2026-10-15", headers=self._headers(502))

        self.assertEqual(200, respuesta.status_code)
        reporte = self.json(respuesta)["report"]
        self.assertEqual(1, len(reporte))
        self.assertEqual("2026-10-15T08:02:00", reporte[0]["firstEntry"])
        self.assertEqual("2026-10-15T17:10:00", reporte[0]["lastExit"])
        self.assertEqual(2, reporte[0]["marks"])
        self.assertEqual(9.1, self.json(respuesta)["statistics"][0]["estimatedHours"])

    def test_leer_lo_guardado_exige_permiso(self):
        respuesta = self.client.get(
            "/kronos/attendance/saved?startDate=2026-10-15&endDate=2026-10-15", headers=self._headers(999))
        self.assertEqual(403, respuesta.status_code)

    def test_un_rango_invalido_se_rechaza(self):
        respuesta = self.client.get(
            "/kronos/attendance/saved?startDate=2026-10-16&endDate=2026-10-15", headers=self._headers(502))
        self.assertEqual(400, respuesta.status_code)


class TestVinculoChecadorEmpleado(BackendTestCase):
    """Fase 2: que empleado del sistema es cada numero del checador."""

    def setUp(self):
        super().setUp()
        from app.models import User
        with transaction_context() as db:
            for id_user, nombre in ((61, "Ana Lopez Diaz"), (62, "Luis Perez Rios")):
                db.add(User(id_user=id_user, created_by=1, full_name=nombre, id_permission=1,
                            id_proyect=1, id_status=1, supervisor=1, user_type="employee",
                            is_employee=True, username=f"empleado-{id_user}"))
            # Un usuario que no es empleado (el administrador del sistema).
            db.add(User(id_user=63, created_by=1, full_name="Administrador del sistema", id_permission=1,
                        id_proyect=1, id_status=1, supervisor=1, user_type="admin",
                        is_employee=False, username="admin-sistema"))
            db.add_all([
                EntityPermission(id_permission=601, entity_name="attendance_employee_link",
                                  scope_create=4, scope_read=4, scope_update=4, scope_delete=4, created_by=1),
                EntityPermission(id_permission=601, entity_name="attendance_record",
                                  scope_create=4, scope_read=4, scope_update=4, scope_delete=4, created_by=1),
                EntityPermission(id_permission=602, entity_name="attendance_employee_link",
                                  scope_create=0, scope_read=4, scope_update=0, scope_delete=0, created_by=1),
            ])

    def _headers(self, id_permission):
        token = jwt.encode({"id_user": 41, "id_permission": id_permission}, SECRET_KEY, algorithm="HS256")
        return {"Authorization": f"Bearer {token}"}

    def _empleados_de_las_checadas(self):
        with transaction_context() as db:
            return {fila.id_user for fila in db.query(AttendanceRecord).all()}

    def test_ligar_rellena_las_checadas_que_ya_estaban(self):
        from app.services.attendance_record_service import ligar_empleado
        importar_eventos_kronos(EVENTOS, EQUIPO["deviceUrl"], 1)
        self.assertEqual({None}, self._empleados_de_las_checadas())

        resultado = ligar_empleado("7", 61, 1)

        self.assertEqual(2, resultado["records_linked"])
        self.assertEqual({61}, self._empleados_de_las_checadas())

    def test_una_importacion_nueva_ya_entra_ligada(self):
        from app.services.attendance_record_service import ligar_empleado
        ligar_empleado("7", 61, 1)
        importar_eventos_kronos(EVENTOS, EQUIPO["deviceUrl"], 1)
        self.assertEqual({61}, self._empleados_de_las_checadas())

    def test_cambiar_de_empleado_cierra_el_vinculo_anterior(self):
        from app.models import AttendanceEmployeeLink
        from app.services.attendance_record_service import ligar_empleado, vinculos_de_empleados
        importar_eventos_kronos(EVENTOS, EQUIPO["deviceUrl"], 1)
        ligar_empleado("7", 61, 1)
        ligar_empleado("7", 62, 1)

        self.assertEqual([{"employee_no": "7", "id_user": 62, "full_name": "Luis Perez Rios"}],
                         vinculos_de_empleados())
        self.assertEqual({62}, self._empleados_de_las_checadas())
        with transaction_context() as db:
            # El vinculo anterior queda como rastro, cerrado.
            self.assertEqual(1, db.query(AttendanceEmployeeLink)
                             .filter(AttendanceEmployeeLink.deletion_date.isnot(None)).count())

    def test_volver_a_ligar_al_mismo_no_duplica(self):
        from app.models import AttendanceEmployeeLink
        from app.services.attendance_record_service import ligar_empleado
        ligar_empleado("7", 61, 1)
        ligar_empleado("7", 61, 1)
        with transaction_context() as db:
            self.assertEqual(1, db.query(AttendanceEmployeeLink).count())

    def test_desligar_deja_las_checadas_sin_empleado(self):
        from app.services.attendance_record_service import desligar_empleado, ligar_empleado
        importar_eventos_kronos(EVENTOS, EQUIPO["deviceUrl"], 1)
        ligar_empleado("7", 61, 1)

        resultado = desligar_empleado("7", 1)

        self.assertEqual(2, resultado["records_unlinked"])
        self.assertEqual({None}, self._empleados_de_las_checadas())

    def test_no_se_liga_a_un_usuario_que_no_existe(self):
        respuesta = self.client.put("/kronos/employee-links/7", json={"id_user": 999},
                                    headers=self._headers(601))
        self.assertEqual(400, respuesta.status_code)

    def test_la_api_liga_lista_y_desliga(self):
        respuesta = self.client.put("/kronos/employee-links/7", json={"id_user": 61}, headers=self._headers(601))
        self.assertEqual(200, respuesta.status_code)

        lista = self.json(self.client.get("/kronos/employee-links", headers=self._headers(602)))
        self.assertEqual([{"employee_no": "7", "id_user": 61, "full_name": "Ana Lopez Diaz"}], lista["links"])

        self.assertEqual(200, self.client.delete("/kronos/employee-links/7", headers=self._headers(601)).status_code)
        self.assertEqual(404, self.client.delete("/kronos/employee-links/7", headers=self._headers(601)).status_code)

    def test_quien_solo_consulta_no_puede_ligar(self):
        respuesta = self.client.put("/kronos/employee-links/7", json={"id_user": 61}, headers=self._headers(602))
        self.assertEqual(403, respuesta.status_code)

    def test_el_reporte_guardado_usa_el_nombre_del_sistema(self):
        from app.services.attendance_record_service import ligar_empleado
        importar_eventos_kronos(EVENTOS, EQUIPO["deviceUrl"], 1)
        ligar_empleado("7", 61, 1)

        respuesta = self.client.get(
            "/kronos/attendance/saved?startDate=2026-10-15&endDate=2026-10-15", headers=self._headers(601))

        self.assertEqual("Ana Lopez Diaz", self.json(respuesta)["report"][0]["name"])

    def test_no_se_liga_a_quien_no_es_empleado(self):
        respuesta = self.client.put("/kronos/employee-links/7", json={"id_user": 63},
                                    headers=self._headers(601))
        self.assertEqual(400, respuesta.status_code)
        self.assertEqual("not_employee", self.json(respuesta)["meta"]["reason"])

    def test_la_lista_para_ligar_solo_trae_empleados(self):
        respuesta = self.client.get("/kronos/employee-options", headers=self._headers(602))
        self.assertEqual(200, respuesta.status_code)
        self.assertEqual([61, 62], [e["id_user"] for e in self.json(respuesta)["employees"]])
