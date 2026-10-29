"""Hoja de incapacidad (revision contable, 2026-10-28).

El empleado reporta su incapacidad y sube la hoja del IMSS (JPG, PNG o PDF de
hasta 10 MB); solo cuenta cuando RH la aprueba. La hoja es un dato medico: solo
la ven el propio empleado y RH. Su jefe no la revisa ni ve la hoja, y el modulo
de Documentos tampoco se la muestra a los demas.

Mismo equipo que test_solicitudes_de_vacaciones: Ana (71) con su jefe Beto (80),
Carla (81) del mismo proyecto y Rocio (82) de RH.
"""
from __future__ import annotations

import tempfile

from app.models import EntityPermission
from app.models.session import transaction_context
from app.services.document_service import DocumentManagementService
from tests.test_services.test_solicitudes_de_vacaciones import ANA, BETO, CARLA, RH, _ConEquipo

PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


class _ConHojas(_ConEquipo):
    def setUp(self):
        super().setUp()
        self._carpeta = tempfile.TemporaryDirectory()
        self._raiz = self.app.config.get("UPLOAD_ROOT")
        self.app.config["UPLOAD_ROOT"] = self._carpeta.name
        with transaction_context() as db:
            db.execute(EntityPermission.__table__.insert().values(
                id_permission=2, entity_name="document", scope_create=4, scope_read=4, scope_update=4,
                scope_delete=4, created_by=1))
            from app.models.document import DocumentCategory
            db.add(DocumentCategory(code="disability_certificate", name="Hoja de incapacidad", created_by=1))

    def tearDown(self):
        self.app.config["UPLOAD_ROOT"] = self._raiz
        self._carpeta.cleanup()
        super().tearDown()

    def reportar(self):
        r = self.client.post("/employee_leave/request", headers=self.h(ANA), json={
            "leave_type": "disability", "disability_type": "general_illness",
            "start_date": "2026-10-06", "end_date": "2026-10-08"})
        self.assertEqual(201, r.status_code)
        return self.json(r)["id_employee_leave"]

    def subir(self, ident, quien=ANA, contenido=PDF, nombre="hoja.pdf"):
        from io import BytesIO
        return self.client.post(f"/employee_leave/{ident}/documents", headers=self.h(quien),
                                data={"file": (BytesIO(contenido), nombre)}, content_type="multipart/form-data")

    def hojas(self, ident, quien):
        return self.client.get(f"/employee_leave/{ident}/documents", headers=self.h(quien))


class TestReportar(_ConHojas):
    def test_el_empleado_la_reporta_pendiente_con_su_tipo(self):
        ident = self.reportar()
        mias = self.json(self.client.get("/employee_leave/mine", headers=self.h(ANA)))["leaves"]
        ausencia = next(a for a in mias if a["id_employee_leave"] == ident)
        self.assertEqual(("requested", "general_illness"), (ausencia["leave_status"], ausencia["disability_type"]))

    def test_solo_rh_la_revisa(self):
        ident = self.reportar()
        self.assertEqual([], self.json(self.client.get("/employee_leave/pending", headers=self.h(BETO)))["requests"])
        self.assertEqual(403, self.client.post(f"/employee_leave/{ident}/approve", headers=self.h(BETO),
                                               json={}).status_code)
        r = self.client.post(f"/employee_leave/{ident}/approve", headers=self.h(RH), json={})
        self.assertEqual(("approved", RH), (self.json(r)["leave_status"], self.json(r)["reviewed_by"]))


class TestHoja(_ConHojas):
    def test_el_empleado_la_sube_y_cada_archivo_es_una_version(self):
        ident = self.reportar()
        self.assertEqual(201, self.subir(ident).status_code)
        self.assertEqual(201, self.subir(ident, contenido=PNG, nombre="foto.png").status_code)
        hojas = self.json(self.hojas(ident, ANA))["documents"]
        self.assertEqual([(2, "foto.png"), (1, "hoja.pdf")], [(h["version"], h["original_filename"]) for h in hojas])
        r = self.client.get(f"/employee_leave/{ident}/documents/1/content", headers=self.h(ANA))
        self.assertEqual((200, PDF), (r.status_code, r.data))

    def test_rh_la_ve_y_tambien_la_puede_subir(self):
        ident = self.reportar()
        self.assertEqual(201, self.subir(ident, quien=RH).status_code)
        self.assertEqual("Rocio RH", self.json(self.hojas(ident, RH))["documents"][0]["uploaded_by_name"])

    def test_ni_el_jefe_ni_otro_empleado_la_ven(self):
        ident = self.reportar()
        self.subir(ident)
        for quien in (BETO, CARLA):
            self.assertEqual(404, self.hojas(ident, quien).status_code)
            self.assertEqual(404, self.client.get(f"/employee_leave/{ident}/documents/1/content",
                                                  headers=self.h(quien)).status_code)
            self.assertEqual(404, self.subir(ident, quien=quien).status_code)

    def test_solo_foto_o_pdf_y_solo_en_incapacidades(self):
        ident = self.reportar()
        r = self.subir(ident, contenido=b"PK\x03\x04" + b"\x00" * 20, nombre="hoja.docx")
        self.assertEqual("documents.invalid_file_type", self.json(r)["error_key"])
        vacaciones = self.json(self.pedir("2026-10-13", "2026-10-14"))["id_employee_leave"]
        self.assertEqual(400, self.subir(vacaciones).status_code)

    def test_en_documentos_solo_la_ven_rh_y_la_duena(self):
        ident = self.reportar()
        self.subir(ident)

        def titulos(quien, permiso):
            datos = DocumentManagementService.list({"id_user": quien, "id_permission": permiso, "id_proyect": 1},
                                                   per_page=50)
            return [d["title"] for d in datos["items"]]

        self.assertEqual(1, len(titulos(ANA, 2)))
        self.assertEqual(1, len(titulos(RH, 961)))
        self.assertEqual([], titulos(CARLA, 2))
        self.assertEqual([], titulos(BETO, 2))
