"""Listado de documentos: filtros por persona, subido por y fechas, y datos para pintar la tabla."""
from __future__ import annotations

from datetime import date

from app.models import CustomerSupplier, Document, DocumentCategory, DocumentRelation, DocumentVersion, User
from app.models.session import transaction_context
from app.services.document_service import DocumentManagementService
from app.utils.errors import AppError
from tests.conftest import BackendTestCase

ADMIN = {"id_user": 1, "id_proyect": 1, "id_permission": 1, "user_type": "admin", "is_superuser": True}
EMPLEADA, OTRO_EMPLEADO, SUBE_UNO, SUBE_DOS, CLIENTE_A, CLIENTE_B = 920, 921, 922, 923, 924, 925


class TestFiltrosDeDocumentos(BackendTestCase):
    def setUp(self):
        super().setUp()
        with transaction_context() as db:
            for user_id, name, tipo in (
                (EMPLEADA, "Elena Empleada", "employee"), (OTRO_EMPLEADO, "Omar Otro", "employee"),
                (SUBE_UNO, "Sara Sube", "employee"), (SUBE_DOS, "Saul Sube", "employee"),
                (CLIENTE_A, "Cliente A", "client"), (CLIENTE_B, "Cliente B", "client"),
            ):
                db.add(User(
                    id_user=user_id, created_by=1, full_name=name, id_permission=1, id_proyect=1, id_status=1,
                    supervisor=1, user_type=tipo, is_employee=tipo == "employee", username=f"filtros-{user_id}",
                ))
            db.flush()
            for customer_id, name in ((CLIENTE_A, "Empresa A"), (CLIENTE_B, "Empresa B")):
                db.add(CustomerSupplier(
                    id_customer_supplier=customer_id, name=name, type="client", id_user=customer_id,
                    contact_name=name, email=f"{customer_id}@example.com", created_by=1,
                ))
            db.flush()
            certificacion = DocumentCategory(code="certification", name="Certificacion", created_by=1)
            recibo = DocumentCategory(code="receipt", name="Recibo", created_by=1)
            db.add_all([certificacion, recibo])
            db.flush()

            def documento(titulo, categoria, subio, emision, *, empleado=None, cliente=None, version_source=None):
                doc = Document(
                    id_proyect=1, id_document_category=categoria.id_document_category, title=titulo,
                    status="issued", issue_date=emision, created_by=subio,
                )
                db.add(doc); db.flush()
                if empleado:
                    db.add(DocumentRelation(id_document=doc.id_document, relation_type="employee", id_employee=empleado, created_by=1))
                if cliente:
                    db.add(DocumentRelation(id_document=doc.id_document, relation_type="customer", id_customer_supplier=cliente, created_by=1))
                if version_source:
                    db.add(DocumentVersion(
                        id_document=doc.id_document, version=1, file_path="documents/x.pdf", original_filename="x.pdf",
                        extension="pdf", mime_type="application/pdf", file_size=1, sha256="0" * 64,
                        source=version_source, generated_by=1,
                    ))
                return doc.id_document

            self.ids = {
                "elena_enero": documento("Constancia Elena", certificacion, SUBE_UNO, date(2026, 1, 10), empleado=EMPLEADA, version_source="uploaded"),
                "elena_junio": documento("Recibo Elena", recibo, SUBE_DOS, date(2026, 6, 10), empleado=EMPLEADA),
                "omar": documento("Constancia Omar", certificacion, SUBE_UNO, date(2026, 3, 1), empleado=OTRO_EMPLEADO),
                "cliente_a": documento("Contrato A", certificacion, SUBE_UNO, date(2026, 2, 1), cliente=CLIENTE_A),
                "cliente_b": documento("Contrato B", certificacion, SUBE_DOS, date(2026, 2, 2), cliente=CLIENTE_B),
                "vale": documento("Vale generado", recibo, SUBE_DOS, date(2026, 7, 1), version_source="generated"),
            }

    def _titulos(self, actor=ADMIN, **filtros):
        return {d["title"] for d in DocumentManagementService.list(actor, 1, 100, filtros)["items"]}

    def test_filters_by_the_employee_the_document_belongs_to(self):
        self.assertEqual(self._titulos(id_employee=EMPLEADA), {"Constancia Elena", "Recibo Elena"})

    def test_filters_by_the_customer_the_document_belongs_to(self):
        self.assertEqual(self._titulos(id_customer_supplier=CLIENTE_A), {"Contrato A"})

    def test_a_document_with_no_person_is_left_out_when_filtering_by_person(self):
        self.assertNotIn("Vale generado", self._titulos(id_employee=EMPLEADA))

    def test_filters_by_who_uploaded_it(self):
        self.assertEqual(self._titulos(created_by=SUBE_DOS), {"Recibo Elena", "Contrato B", "Vale generado"})

    def test_filters_by_category(self):
        with transaction_context() as db:
            recibo = db.query(DocumentCategory).filter_by(code="receipt").one().id_document_category
        self.assertEqual(self._titulos(id_document_category=recibo), {"Recibo Elena", "Vale generado"})

    def test_filters_by_issue_date_range_inclusive(self):
        self.assertEqual(self._titulos(issue_date_from="2026-02-01", issue_date_to="2026-03-01"),
                         {"Contrato A", "Contrato B", "Constancia Omar"})

    def test_filters_combine_with_and(self):
        self.assertEqual(self._titulos(id_employee=EMPLEADA, created_by=SUBE_UNO), {"Constancia Elena"})
        self.assertEqual(self._titulos(id_employee=EMPLEADA, issue_date_from="2026-05-01"), {"Recibo Elena"})

    def test_the_total_counts_the_filtered_rows_not_the_page(self):
        pagina = DocumentManagementService.list(ADMIN, 1, 1, {"id_employee": EMPLEADA})
        self.assertEqual((len(pagina["items"]), pagina["total"]), (1, 2))

    def test_a_client_cannot_widen_its_scope_by_filtering_for_someone_else(self):
        cliente = {"id_user": CLIENTE_A, "id_proyect": 1, "id_permission": 1, "user_type": "client"}
        self.assertEqual(self._titulos(cliente), {"Contrato A"})
        self.assertEqual(self._titulos(cliente, id_customer_supplier=CLIENTE_B), set())

    def test_the_list_carries_what_the_table_paints(self):
        items = {d["title"]: d for d in DocumentManagementService.list(ADMIN, 1, 100)["items"]}
        elena = items["Constancia Elena"]
        self.assertEqual((elena["category_name"], elena["category_code"]), ("Certificacion", "certification"))
        self.assertEqual(elena["created_by_name"], "Sara Sube")
        self.assertEqual(elena["related"], [{"relation_type": "employee", "target": "employee", "id": EMPLEADA, "name": "Elena Empleada"}])
        self.assertEqual(items["Contrato A"]["related"][0]["name"], "Empresa A")
        self.assertEqual(items["Vale generado"]["related"], [])

    def test_only_documents_with_a_non_manual_version_are_system_generated(self):
        items = {d["title"]: d["system_generated"] for d in DocumentManagementService.list(ADMIN, 1, 100)["items"]}
        self.assertTrue(items["Vale generado"])
        self.assertFalse(items["Constancia Elena"])  # version subida a mano
        self.assertFalse(items["Contrato A"])  # sin version

    def test_the_detail_also_carries_the_enriched_fields(self):
        detalle = DocumentManagementService.get(self.ids["vale"], ADMIN)
        self.assertTrue(detalle["system_generated"])
        self.assertEqual(detalle["category_name"], "Recibo")
        self.assertIn("versions", detalle)

    def test_the_uploaders_list_has_each_person_once_and_follows_the_scope(self):
        nombres = [u["full_name"] for u in DocumentManagementService.uploaders(ADMIN)]
        self.assertEqual(nombres, ["Sara Sube", "Saul Sube"])
        cliente = {"id_user": CLIENTE_A, "id_proyect": 1, "id_permission": 1, "user_type": "client"}
        self.assertEqual([u["full_name"] for u in DocumentManagementService.uploaders(cliente)], ["Sara Sube"])

    def test_invalid_filter_values_are_a_400_not_a_500(self):
        for filtros in ({"created_by": "abc"}, {"id_employee": "0"}, {"issue_date_from": "ayer"}):
            with self.assertRaises(AppError) as caught:
                DocumentManagementService.list(ADMIN, 1, 100, filtros)
            self.assertEqual(caught.exception.status_code, 400)
