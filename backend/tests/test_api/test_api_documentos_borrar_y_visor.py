"""Borrar documentos por permiso, el candado de los generados por el sistema y el visor en linea."""
from __future__ import annotations

import shutil
import tempfile
from io import BytesIO
from unittest.mock import patch

from app.models import Document, DocumentCategory, DocumentVersion, User
from app.models.entity_permission import EntityPermission
from app.models.session import transaction_context
from tests.conftest import BackendTestCase

PDF = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\ntest\n%%EOF"
DOCX = b"PK\x03\x04" + b"0" * 40

ROL_BORRA, ROL_SOLO_LEE, ROL_SIN_VISOR = 701, 702, 703
BORRA = {"id_user": 71, "id_permission": ROL_BORRA, "id_proyect": 1, "user_type": "employee"}
SOLO_LEE = {"id_user": 72, "id_permission": ROL_SOLO_LEE, "id_proyect": 1, "user_type": "employee"}
SIN_VISOR = {"id_user": 73, "id_permission": ROL_SIN_VISOR, "id_proyect": 1, "user_type": "employee"}


class TestBorrarYVisor(BackendTestCase):
    def setUp(self):
        super().setUp()
        self.directorio = tempfile.mkdtemp()
        self.app.config["UPLOAD_ROOT"] = self.directorio
        with transaction_context() as db:
            for user_id in (71, 72, 73):
                db.add(User(id_user=user_id, created_by=1, full_name=f"Usuario {user_id}", id_permission=1,
                            id_proyect=1, id_status=1, supervisor=1, user_type="employee", is_employee=True,
                            username=f"borrar-{user_id}"))
            db.flush()
            for rol, document, version in ((ROL_BORRA, (4, 4, 4, 4), (4, 4, 4, 0)), (ROL_SOLO_LEE, (0, 4, 0, 0), (0, 4, 0, 0)),
                                           (ROL_SIN_VISOR, (0, 4, 0, 0), (0, 0, 0, 0))):
                for entidad, (c, r, u, d) in (("document", document), ("document_version", version)):
                    db.add(EntityPermission(id_permission=rol, entity_name=entidad, scope_create=c, scope_read=r,
                                            scope_update=u, scope_delete=d, created_by=1))
            self.categoria = DocumentCategory(code="certification", name="Certificacion", created_by=1)
            db.add(self.categoria)

    def tearDown(self):
        shutil.rmtree(self.directorio, ignore_errors=True)
        super().tearDown()

    def _request(self, actor, method, path, **kwargs):
        with patch("app.utils.auth.jwt.decode", return_value=actor):
            return self.client.open(path, method=method, headers={"Authorization": "Bearer documentos-test"}, **kwargs)

    def _subir(self, archivo=PDF, nombre="constancia.pdf"):
        respuesta = self._request(BORRA, "POST", "/document/", content_type="multipart/form-data", data={
            "file": (BytesIO(archivo), nombre), "title": "Constancia", "id_document_category": str(self.categoria.id_document_category),
            "relation_type": "employee", "id_employee": "71",
        })
        self.assertEqual(respuesta.status_code, 201, respuesta.get_data(as_text=True))
        return self.json(respuesta)["document"]["id_document"]

    def _documento_del_sistema(self, source="generated"):
        with transaction_context() as db:
            doc = Document(id_proyect=1, id_document_category=self.categoria.id_document_category,
                           title="Vale generado", status="issued", created_by=1)
            db.add(doc); db.flush()
            db.add(DocumentVersion(id_document=doc.id_document, version=1, file_path="documents/x.pdf", original_filename="x.pdf",
                                   extension="pdf", mime_type="application/pdf", file_size=1, sha256="0" * 64,
                                   source=source, generated_by=1))
            return doc.id_document

    # --- borrar ---

    def test_a_role_with_delete_permission_removes_a_manual_document(self):
        id_document = self._subir()
        self.assertEqual(self._request(BORRA, "DELETE", f"/document/{id_document}").status_code, 204)
        self.assertEqual(self._request(BORRA, "GET", f"/document/{id_document}").status_code, 404)
        listado = self.json(self._request(BORRA, "GET", "/document/"))
        self.assertEqual(listado["items"], [])

    def test_a_role_without_delete_permission_gets_403_and_the_document_stays(self):
        id_document = self._subir()
        respuesta = self._request(SOLO_LEE, "DELETE", f"/document/{id_document}")
        self.assertEqual(respuesta.status_code, 403)
        self.assertEqual(self._request(SOLO_LEE, "GET", f"/document/{id_document}").status_code, 200)

    def test_a_system_generated_document_cannot_be_deleted_even_with_permission(self):
        for source in ("generated", "signed_scan"):
            with self.subTest(source=source):
                id_document = self._documento_del_sistema(source)
                respuesta = self._request(BORRA, "DELETE", f"/document/{id_document}")
                self.assertEqual(respuesta.status_code, 409)
                self.assertEqual(self.json(respuesta)["error_key"], "documents.system_generated_not_deletable")
                self.assertEqual(self._request(BORRA, "GET", f"/document/{id_document}").status_code, 200)

    def test_the_superuser_cannot_delete_a_system_generated_document_either(self):
        id_document = self._documento_del_sistema()
        admin = {"id_user": 1, "id_proyect": 1, "id_permission": 1, "user_type": "admin", "is_superuser": True}
        self.assertEqual(self._request(admin, "DELETE", f"/document/{id_document}").status_code, 409)

    # --- cerrar el hueco de source ---

    def test_a_client_cannot_mark_a_new_version_as_system_generated(self):
        id_document = self._subir()
        for source in ("generated", "signed_scan", "otro"):
            with self.subTest(source=source):
                respuesta = self._request(BORRA, "POST", f"/document/{id_document}/versions", content_type="multipart/form-data",
                                          data={"file": (BytesIO(PDF), "nueva.pdf"), "source": source})
                self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(self._request(BORRA, "DELETE", f"/document/{id_document}").status_code, 204)

    def test_a_plain_new_version_is_accepted_and_stays_deletable(self):
        id_document = self._subir()
        respuesta = self._request(BORRA, "POST", f"/document/{id_document}/versions", content_type="multipart/form-data",
                                  data={"file": (BytesIO(PDF), "nueva.pdf")})
        self.assertEqual(respuesta.status_code, 201)
        self.assertEqual(self._request(BORRA, "DELETE", f"/document/{id_document}").status_code, 204)

    # --- visor ---

    def test_a_pdf_is_served_inline_for_the_viewer_and_as_attachment_for_download(self):
        id_document = self._subir()
        en_linea = self._request(SOLO_LEE, "GET", f"/document/{id_document}/versions/1/content")
        self.assertEqual(en_linea.status_code, 200)
        self.assertEqual(en_linea.mimetype, "application/pdf")
        self.assertTrue(en_linea.headers["Content-Disposition"].startswith("inline"))
        self.assertEqual(en_linea.headers["X-Content-Type-Options"], "nosniff")
        descarga = self._request(SOLO_LEE, "GET", f"/document/{id_document}/versions/1/content?download=1")
        self.assertTrue(descarga.headers["Content-Disposition"].startswith("attachment"))

    def test_a_docx_is_never_served_inline(self):
        id_document = self._subir(DOCX, "carta.docx")
        respuesta = self._request(SOLO_LEE, "GET", f"/document/{id_document}/versions/1/content")
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.headers["Content-Disposition"].startswith("attachment"))

    def test_the_viewer_demands_read_permission_on_document_version(self):
        id_document = self._subir()
        respuesta = self._request(SIN_VISOR, "GET", f"/document/{id_document}/versions/1/content")
        self.assertEqual(respuesta.status_code, 403)
