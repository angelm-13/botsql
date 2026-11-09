"""Vencimiento por categoria al cargar un documento: certification obligatorio; employee y supplier, la fecha o
"sin vencimiento"; el resto opcional (ver `CATEGORIAS_VENCIMIENTO_*` en document_service.py)."""
from __future__ import annotations

import shutil
import tempfile
from io import BytesIO
from unittest.mock import patch

from app.models import CustomerSupplier, DocumentCategory, User
from app.models.entity_permission import EntityPermission
from app.models.session import transaction_context
from tests.conftest import BackendTestCase

PDF = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\ntest\n%%EOF"
ROL = 710
ACTOR = {"id_user": 74, "id_permission": ROL, "id_proyect": 1, "user_type": "employee"}
CATEGORIAS = ("certification", "employee", "supplier", "customer", "receipt")


class TestVencimientoPorCategoria(BackendTestCase):
    def setUp(self):
        super().setUp()
        self.directorio = tempfile.mkdtemp()
        self.app.config["UPLOAD_ROOT"] = self.directorio
        with transaction_context() as db:
            db.add(User(id_user=74, created_by=1, full_name="Usuario 74", id_permission=1, id_proyect=1, id_status=1,
                        supervisor=1, user_type="employee", is_employee=True, username="vencimiento-74"))
            db.flush()
            db.add(CustomerSupplier(id_customer_supplier=741, name="Proveedor Uno", type="supplier", id_user=74,
                                    contact_name="Proveedor Uno", email="p741@example.com", created_by=1))
            for entidad in ("document", "document_version"):
                db.add(EntityPermission(id_permission=ROL, entity_name=entidad, scope_create=4, scope_read=4,
                                        scope_update=4, scope_delete=0, created_by=1))
            self.categorias = {}
            for codigo in CATEGORIAS:
                categoria = DocumentCategory(code=codigo, name=codigo.capitalize(), created_by=1)
                db.add(categoria)
                db.flush()
                self.categorias[codigo] = categoria.id_document_category

    def tearDown(self):
        shutil.rmtree(self.directorio, ignore_errors=True)
        super().tearDown()

    def _request(self, method, path, **kwargs):
        with patch("app.utils.auth.jwt.decode", return_value=ACTOR):
            return self.client.open(path, method=method, headers={"Authorization": "Bearer vencimiento-test"}, **kwargs)

    def _subir(self, codigo, **campos):
        relacion = ({"relation_type": "supplier", "id_customer_supplier": "741"} if codigo == "supplier"
                    else {"relation_type": "employee", "id_employee": "74"})
        datos = {"file": (BytesIO(PDF), "doc.pdf"), "title": "Doc", "id_document_category": str(self.categorias[codigo]),
                 **relacion, **campos}
        return self._request("POST", "/document/", content_type="multipart/form-data", data=datos)

    def test_certification_requires_an_expiration_date_and_has_no_way_out(self):
        for campos in ({}, {"no_expiration": "true"}, {"expiration_date": ""}):
            with self.subTest(campos=campos):
                respuesta = self._subir("certification", **campos)
                self.assertEqual(respuesta.status_code, 400, respuesta.get_data(as_text=True))
                cuerpo = self.json(respuesta)
                self.assertEqual(cuerpo["error_key"], "documents.expiration_required")
                self.assertEqual(cuerpo["meta"]["category"], "certification")
                self.assertFalse(cuerpo["meta"]["can_declare_no_expiration"])
        self.assertEqual(self._subir("certification", expiration_date="2030-06-30").status_code, 201)

    def test_employee_and_supplier_need_the_date_or_the_declaration_of_no_expiration(self):
        for codigo in ("employee", "supplier"):
            with self.subTest(codigo=codigo):
                faltante = self._subir(codigo)
                self.assertEqual(faltante.status_code, 400)
                self.assertEqual(self.json(faltante)["error_key"], "documents.expiration_required")
                self.assertTrue(self.json(faltante)["meta"]["can_declare_no_expiration"])
                self.assertEqual(self._subir(codigo, expiration_date="2031-01-15").status_code, 201)
                sin_vencimiento = self._subir(codigo, no_expiration="true")
                self.assertEqual(sin_vencimiento.status_code, 201, sin_vencimiento.get_data(as_text=True))
                self.assertIsNone(self.json(sin_vencimiento)["document"]["expiration_date"])

    def test_declaring_no_expiration_and_giving_a_date_contradict_each_other(self):
        respuesta = self._subir("employee", no_expiration="true", expiration_date="2031-01-15")
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(self.json(respuesta)["error_key"], "errors.invalid_field")
        self.assertEqual(self.json(respuesta)["meta"]["field"], "no_expiration")

    def test_the_other_categories_keep_the_date_optional(self):
        for codigo in ("customer", "receipt"):
            with self.subTest(codigo=codigo):
                respuesta = self._subir(codigo)
                self.assertEqual(respuesta.status_code, 201, respuesta.get_data(as_text=True))

    def test_the_issue_and_expiration_dates_are_saved_and_expiration_cannot_precede_issue(self):
        creado = self._subir("certification", issue_date="2026-01-10", expiration_date="2027-01-10")
        self.assertEqual(creado.status_code, 201)
        documento = self.json(creado)["document"]
        self.assertEqual((documento["issue_date"], documento["expiration_date"]), ("2026-01-10", "2027-01-10"))
        invertido = self._subir("certification", issue_date="2026-05-01", expiration_date="2026-04-01")
        self.assertEqual(invertido.status_code, 400)
        self.assertEqual(self.json(invertido)["meta"]["field"], "expiration_date")

    def test_a_certification_cannot_lose_its_expiration_date_by_editing_it(self):
        id_document = self.json(self._subir("certification", expiration_date="2030-06-30"))["document"]["id_document"]
        titulo = self._request("PUT", f"/document/{id_document}", json={"title": "Otro titulo"})
        self.assertEqual(titulo.status_code, 200)
        borrado = self._request("PUT", f"/document/{id_document}", json={"expiration_date": ""})
        self.assertEqual(borrado.status_code, 400)
        self.assertEqual(self.json(borrado)["error_key"], "documents.expiration_required")
        cambiado = self._request("PUT", f"/document/{id_document}", json={"expiration_date": "2032-02-02"})
        self.assertEqual(cambiado.status_code, 200)
        self.assertEqual(self.json(cambiado)["expiration_date"], "2032-02-02")
