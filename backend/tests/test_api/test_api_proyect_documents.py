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
        with transaction_context() as db:
            db.add_all([
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

        delete = self._request(self.supervisor, "DELETE", f"/proyect/documents/{document_id}")
        self.assertEqual(200, delete.status_code)
        listado = self._request(self.supervisor, "GET", f"/proyect/{project_id}/documents")
        self.assertEqual(0, len(self.json(listado)["items"]))

    def test_an_actor_without_scope_cannot_see_the_attachment(self):
        project_id = self._create_project()
        self._request(
            self.supervisor, "POST", f"/proyect/{project_id}/documents",
            data={"file": (BytesIO(PDF_BYTES), "requisitos.pdf")},
            content_type="multipart/form-data",
        )

        response = self._request(self.other_supervisor, "GET", f"/proyect/{project_id}/documents")
        self.assertEqual(404, response.status_code)
