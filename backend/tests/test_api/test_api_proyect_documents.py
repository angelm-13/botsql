from __future__ import annotations

import shutil
import tempfile
from io import BytesIO
from unittest.mock import patch

from app.models.entity_permission import EntityPermission
from app.models.session import transaction_context
from tests.conftest import BackendTestCase


PDF_BYTES = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\ntest\n%%EOF"
DOCX_BYTES = b"PK\x03\x04" + b"0" * 40  # firma real de un .docx (zip/OOXML)
XLSX_BYTES = b"PK\x03\x04" + b"0" * 40  # mismo contenedor zip/OOXML que docx
XLS_BYTES = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"0" * 40  # firma real OLE2
DWG_BYTES = b"AC1027" + b"0" * 40  # firma real de un DWG (AutoCAD 2013+)
DXF_BYTES = b"0\nSECTION\n2\nHEADER\n0\nENDSEC\n0\nEOF\n"  # DXF ASCII real
STEP_BYTES = b"ISO-10303-21;\nHEADER;\nENDSEC;\nEND-ISO-10303-21;\n"  # STEP real


class TestProyectDocumentsApi(BackendTestCase):
    def setUp(self):
        super().setUp()
        self.supervisor = {"id_user": 11, "id_permission": 101}
        self.other_supervisor = {"id_user": 12, "id_permission": 102}
        self.admin = {"id_user": 1, "is_superuser": True, "id_proyect": 1}
        # Ve todos los proyectos y tiene las dos capacidades de adjuntos en el Gestor.
        self.manager = {"id_user": 13, "id_permission": 103}
        with transaction_context() as db:
            db.add_all([
                EntityPermission(id_permission=103, entity_name="proyect", scope_read=4, scope_update=4, created_by=13),
                EntityPermission(id_permission=103, entity_name="project_document_upload", scope_read=4, created_by=13),
                EntityPermission(id_permission=103, entity_name="project_document_delete", scope_read=4, created_by=13),
                # Propios: ver lo ajeno lo da "Todos" en el Gestor (2026-10-16).
                EntityPermission(id_permission=101, entity_name="proyect", scope_create=4, scope_read=1, scope_update=1, created_by=11),
                EntityPermission(id_permission=102, entity_name="proyect", scope_create=4, scope_read=1, scope_update=1, created_by=12),
            ])
        self._upload_dir = tempfile.mkdtemp()
        self.app.config["UPLOAD_ROOT"] = self._upload_dir

    def tearDown(self):
        shutil.rmtree(self._upload_dir, ignore_errors=True)
        super().tearDown()

    def _request(self, actor, method, path, **kwargs):
        with patch("app.utils.auth.jwt.decode", return_value=actor):
            return self.client.open(
                path, method=method,
                headers={"Authorization": "Bearer proyecto-adjuntos-test"},
                **kwargs,
            )

    def _create_project(self, actor=None):
        response = self._request(actor or self.supervisor, "POST", "/proyect/", json={
            "id_customer_supplier": 1,
            "proyect_description": "Instalación de fachada",
        })
        self.assertEqual(response.status_code, 201)
        return self.json(response)["id_proyect"]

    def test_uploads_a_valid_pdf(self):
        project_id = self._create_project()

        response = self._request(
            self.supervisor, "POST", f"/proyect/{project_id}/documents",
            data={"file": (BytesIO(PDF_BYTES), "requisitos.pdf"), "title": "Requisitos"},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 201)
        adjunto = self.json(response)
        self.assertEqual("requisitos.pdf", adjunto["original_filename"])
        self.assertEqual("pdf", adjunto["extension"])
        self.assertNotIn("file_path", adjunto)

        listado = self._request(self.supervisor, "GET", f"/proyect/{project_id}/documents")
        self.assertEqual(1, len(self.json(listado)["items"]))

    def test_uploads_a_valid_docx(self):
        project_id = self._create_project()

        response = self._request(
            self.supervisor, "POST", f"/proyect/{project_id}/documents",
            data={"file": (BytesIO(DOCX_BYTES), "requisitos.docx")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual("docx", self.json(response)["extension"])

    def test_uploads_a_valid_dxf(self):
        project_id = self._create_project()

        response = self._request(
            self.supervisor, "POST", f"/proyect/{project_id}/documents",
            data={"file": (BytesIO(DXF_BYTES), "plano.dxf")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual("dxf", self.json(response)["extension"])

    def test_uploads_a_valid_dwg(self):
        project_id = self._create_project()

        response = self._request(
            self.supervisor, "POST", f"/proyect/{project_id}/documents",
            data={"file": (BytesIO(DWG_BYTES), "plano.dwg")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual("dwg", self.json(response)["extension"])

    def test_uploads_a_valid_xlsx(self):
        project_id = self._create_project()

        response = self._request(
            self.supervisor, "POST", f"/proyect/{project_id}/documents",
            data={"file": (BytesIO(XLSX_BYTES), "materiales.xlsx")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual("xlsx", self.json(response)["extension"])

    def test_uploads_a_valid_xls(self):
        project_id = self._create_project()

        response = self._request(
            self.supervisor, "POST", f"/proyect/{project_id}/documents",
            data={"file": (BytesIO(XLS_BYTES), "materiales.xls")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual("xls", self.json(response)["extension"])

    def test_uploads_a_valid_step(self):
        project_id = self._create_project()

        response = self._request(
            self.supervisor, "POST", f"/proyect/{project_id}/documents",
            data={"file": (BytesIO(STEP_BYTES), "pieza.step")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual("step", self.json(response)["extension"])

    def test_rejects_a_dxf_that_is_not_actually_text(self):
        """La validacion de contenido para DXF sigue vigente, no es "confiar en la extension"."""
        project_id = self._create_project()

        response = self._request(
            self.supervisor, "POST", f"/proyect/{project_id}/documents",
            data={"file": (BytesIO(b"\x00\x01\x02esto no es un dxf"), "falso.dxf")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual("documents.mime_mismatch", self.json(response)["error_key"])

    def test_the_generic_documents_endpoint_still_rejects_dxf(self):
        """La lista ampliada es solo de adjuntos de proyecto, no se filtro al modulo compartido."""
        admin = {"id_user": 1, "is_superuser": True, "id_proyect": 1}

        response = self._request(
            admin, "POST", "/document/",
            data={"file": (BytesIO(DXF_BYTES), "plano.dxf")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual("documents.invalid_file_type", self.json(response)["error_key"])

    def test_rejects_a_disallowed_extension(self):
        project_id = self._create_project()

        response = self._request(
            self.supervisor, "POST", f"/proyect/{project_id}/documents",
            data={"file": (BytesIO(b"echo hola"), "script.sh")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual("documents.invalid_file_type", self.json(response)["error_key"])

    def test_rejects_a_mime_mismatch(self):
        project_id = self._create_project()

        response = self._request(
            self.supervisor, "POST", f"/proyect/{project_id}/documents",
            data={"file": (BytesIO(b"esto no es un pdf de verdad"), "falso.pdf")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual("documents.mime_mismatch", self.json(response)["error_key"])

    def test_downloads_and_deletes_an_attachment(self):
        project_id = self._create_project()
        upload = self._request(
            self.supervisor, "POST", f"/proyect/{project_id}/documents",
            data={"file": (BytesIO(PDF_BYTES), "requisitos.pdf")},
            content_type="multipart/form-data",
        )
        document_id = self.json(upload)["id_proyect_document"]

        download = self._request(self.supervisor, "GET", f"/proyect/documents/{document_id}/content")
        self.assertEqual(200, download.status_code)
        self.assertEqual(PDF_BYTES, download.data)

        delete = self._request(self.manager, "DELETE", f"/proyect/documents/{document_id}")
        self.assertEqual(200, delete.status_code)
        listado = self._request(self.supervisor, "GET", f"/proyect/{project_id}/documents")
        self.assertEqual(0, len(self.json(listado)["items"]))

    def _sube(self, actor, project_id):
        return self._request(
            actor, "POST", f"/proyect/{project_id}/documents",
            data={"file": (BytesIO(PDF_BYTES), "requisitos.pdf")},
            content_type="multipart/form-data",
        )

    def test_the_uploader_cannot_delete_without_the_capability(self):
        project_id = self._create_project()
        document_id = self.json(self._sube(self.supervisor, project_id))["id_proyect_document"]

        borrar = self._request(self.supervisor, "DELETE", f"/proyect/documents/{document_id}")

        self.assertEqual(403, borrar.status_code)
        self.assertEqual("errors.project_attachment_delete_denied", self.json(borrar)["error_key"])
        listado = self._request(self.supervisor, "GET", f"/proyect/{project_id}/documents")
        self.assertEqual(1, len(self.json(listado)["items"]))

    def test_the_super_user_deletes_without_a_row_in_the_manager(self):
        project_id = self._create_project()
        document_id = self.json(self._sube(self.supervisor, project_id))["id_proyect_document"]
        self.assertEqual(200, self._request(
            self.admin, "DELETE", f"/proyect/documents/{document_id}").status_code)

    def test_only_the_responsible_uploads_unless_the_manager_grants_it(self):
        project_id = self._create_project()
        # Ve y edita todo (Todos), pero no es el responsable y no tiene la capacidad.
        with transaction_context() as db:
            db.add(EntityPermission(id_permission=104, entity_name="proyect", scope_read=4,
                                    scope_update=4, created_by=14))
        sin_capacidad = {"id_user": 14, "id_permission": 104}

        rechazo = self._sube(sin_capacidad, project_id)
        self.assertEqual(403, rechazo.status_code)
        self.assertEqual("errors.project_attachment_leader_only", self.json(rechazo)["error_key"])

        self.assertEqual(201, self._sube(self.supervisor, project_id).status_code)   # el responsable
        self.assertEqual(201, self._sube(self.manager, project_id).status_code)      # la capacidad

    def test_a_capability_without_project_update_still_reaches_the_upload(self):
        """Gerente Comercial solo CONSULTA proyectos: la capacidad abre la puerta sola."""
        project_id = self._create_project()
        with transaction_context() as db:
            db.add_all([
                EntityPermission(id_permission=105, entity_name="proyect", scope_read=4, created_by=15),
                EntityPermission(id_permission=105, entity_name="project_document_upload",
                                 scope_read=4, created_by=15),
                EntityPermission(id_permission=105, entity_name="project_document_delete",
                                 scope_read=4, created_by=15),
            ])
        solo_consulta = {"id_user": 15, "id_permission": 105}

        subida = self._sube(solo_consulta, project_id)
        self.assertEqual(201, subida.status_code)
        borrar = self._request(solo_consulta, "DELETE",
                               f"/proyect/documents/{self.json(subida)['id_proyect_document']}")
        self.assertEqual(200, borrar.status_code)

    def test_a_message_or_attachment_notifies_the_involved(self):
        from app.models.notification import Notification

        project_id = self._create_project()
        response = self._request(self.admin, "POST", f"/proyect/{project_id}/messages",
                                 json={"content": "Instalar la malla al marco"})
        self.assertEqual(201, response.status_code)
        self._sube(self.manager, project_id)
        with transaction_context() as db:
            avisos = db.query(Notification).filter(Notification.id_proyect == project_id).all()
            # El responsable (11) se entera de las dos cosas; quien las hizo, no.
            self.assertEqual([11, 11], sorted(a.id_user_recipient for a in avisos
                                              if a.id_user_recipient == 11))
            self.assertNotIn(13, [a.id_user_recipient for a in avisos])

    def test_an_actor_without_scope_cannot_see_the_attachment(self):
        project_id = self._create_project()
        self._request(
            self.supervisor, "POST", f"/proyect/{project_id}/documents",
            data={"file": (BytesIO(PDF_BYTES), "requisitos.pdf")},
            content_type="multipart/form-data",
        )

        response = self._request(self.other_supervisor, "GET", f"/proyect/{project_id}/documents")
        self.assertEqual(404, response.status_code)
