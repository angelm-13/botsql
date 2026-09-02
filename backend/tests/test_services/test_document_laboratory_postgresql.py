from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from sqlalchemy import delete

from app.models import (
    CustomerSupplier, Document, DocumentRelation, DocumentVersion, LaboratoryEquipment,
    LaboratoryServiceOrder, LaboratoryServiceOrderStatusHistory, User,
)
from app.models.session import engine, transaction_context
from app.services.document_service import DocumentManagementService, SecureDocumentStorage
from app.services.laboratory_report_service import LaboratoryReportService
from app.services.laboratory_service import LaboratoryService
from app.utils.errors import AppError


ADMIN = {"id_user": 1, "id_proyect": 1, "id_permission": 1, "user_type": "admin", "is_superuser": True}
CLIENT_A = {"id_user": 910, "id_proyect": 1, "id_permission": 1, "user_type": "client"}
CLIENT_B = {"id_user": 911, "id_proyect": 1, "id_permission": 1, "user_type": "client"}


@unittest.skipUnless(engine.dialect.name == "postgresql", "Estas pruebas requieren PostgreSQL")
class DocumentLaboratoryPostgresqlTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.storage = SecureDocumentStorage(self.temporary.name)
        with transaction_context() as db:
            db.execute(delete(DocumentRelation))
            db.execute(delete(DocumentVersion))
            db.execute(delete(Document))
            db.execute(delete(LaboratoryServiceOrderStatusHistory))
            db.execute(delete(LaboratoryServiceOrder))
            db.execute(delete(LaboratoryEquipment))
            db.query(CustomerSupplier).filter(CustomerSupplier.id_customer_supplier.in_([910, 911])).delete(synchronize_session=False)
            db.query(User).filter(User.id_user.in_([910, 911, 912])).delete(synchronize_session=False)
            for user_id, name, user_type in ((910, "Cliente Uno", "client"), (911, "Cliente Dos", "client"), (912, "Tecnica Uno", "employee")):
                db.add(User(
                    id_user=user_id, created_by=1, full_name=name, id_permission=1, id_proyect=1,
                    id_status=1, supervisor=1, user_type=user_type, is_employee=user_id == 912,
                    username=f"docs-user-{user_id}",
                ))
            db.flush()
            for customer_id, user_id, name in ((910, 910, "Empresa Uno"), (911, 911, "Empresa Dos")):
                db.add(CustomerSupplier(
                    id_customer_supplier=customer_id, name=name, type="client", id_user=user_id,
                    contact_name=name, email=f"{user_id}@example.com", created_by=1,
                ))

    def tearDown(self):
        self.temporary.cleanup()

    def _order(self):
        equipment = LaboratoryService.create_equipment(ADMIN, {
            "id_customer_supplier": 910, "equipment_type": "Analizador", "brand": "Tyakxa",
            "model": "TX-1", "serial_number": "TEST-SN-001",
        })
        return LaboratoryService.create_order(ADMIN, {
            "id_customer_supplier": 910, "id_laboratory_equipment": equipment["id_laboratory_equipment"],
            "contact_name": "Cliente Uno", "reported_failure": "No enciende", "id_technician": None,
            "delivered_accessories": "Cable", "reception_condition": "Uso normal",
        })

    def test_validates_extension_signature_and_size(self):
        self.assertEqual(("pdf", "application/pdf"), self.storage.validate(b"%PDF-1.4\n%%EOF", "orden.pdf"))
        self.assertEqual(("png", "image/png"), self.storage.validate(b"\x89PNG\r\n\x1a\nrest", "foto.png"))
        self.assertEqual(("jpg", "image/jpeg"), self.storage.validate(b"\xff\xd8\xffrest", "foto.jpg"))
        for content, filename in ((b"not a pdf", "orden.pdf"), (b"%PDF-1.4", "orden.exe"), (b"", "orden.pdf")):
            with self.assertRaises(AppError):
                self.storage.validate(content, filename)

    def test_document_is_visible_only_to_related_customer(self):
        category_id = DocumentManagementService.categories()[0]["id_document_category"]
        created = DocumentManagementService.create_with_version(CLIENT_A, {
            "id_document_category": category_id, "title": "Documento privado",
            "relation_type": "customer", "id_customer_supplier": 910,
        }, b"%PDF-1.4\n%%EOF", "privado.pdf", self.storage)
        document_id = created["document"]["id_document"]
        self.assertEqual(document_id, DocumentManagementService.get(document_id, CLIENT_A)["id_document"])
        with self.assertRaises(AppError) as denied:
            DocumentManagementService.get(document_id, CLIENT_B)
        self.assertEqual(404, denied.exception.status_code)

    def test_document_can_be_related_to_employee_selector(self):
        self.assertEqual([{"id_user": 912, "full_name": "Tecnica Uno"}], DocumentManagementService.employees(ADMIN))
        category_id = DocumentManagementService.categories()[0]["id_document_category"]
        created = DocumentManagementService.create_with_version(ADMIN, {
            "id_document_category": category_id, "title": "Documento de empleado",
            "relation_type": "employee", "id_employee": 912,
        }, b"%PDF-1.4\n%%EOF", "empleado.pdf", self.storage)
        document = DocumentManagementService.get(created["document"]["id_document"], ADMIN)
        self.assertEqual(912, document["relations"][0]["id_employee"])

    def test_duplicate_equipment_serial_returns_conflict(self):
        payload = {
            "id_customer_supplier": 910, "equipment_type": "Analizador",
            "serial_number": "TEST-SN-DUPLICATE",
        }
        LaboratoryService.create_equipment(ADMIN, payload)
        with self.assertRaises(AppError) as duplicate:
            LaboratoryService.create_equipment(ADMIN, {**payload, "serial_number": "test-sn-duplicate"})
        self.assertEqual(409, duplicate.exception.status_code)
        self.assertEqual("errors.duplicate_resource", duplicate.exception.message_key)

    def test_order_transitions_and_history(self):
        order = self._order()
        order_id = order["id_laboratory_service_order"]
        with self.assertRaises(AppError):
            LaboratoryService.transition(order_id, ADMIN, "delivered")
        LaboratoryService.transition(order_id, ADMIN, "diagnosing")
        LaboratoryService.update_diagnosis(order_id, ADMIN, {
            "technical_diagnosis": "Fuente danada", "recommended_repair": "Cambiar fuente",
            "estimated_budget": "1250.50", "estimated_repair_time": "3 dias",
        })
        LaboratoryService.transition(order_id, ADMIN, "pending_authorization")
        history = LaboratoryService.history(order_id, ADMIN)
        self.assertEqual(["received", "diagnosing", "pending_authorization"], [item["new_status"] for item in history])

    def test_pdf_regeneration_and_signed_copy_preserve_versions(self):
        order = self._order()
        order_id = order["id_laboratory_service_order"]
        LaboratoryService.update_diagnosis(order_id, ADMIN, {
            "technical_diagnosis": "Diagnostico extenso. " * 500,
            "recommended_repair": "Reemplazo de fuente", "estimated_budget": "1250.50",
        })
        first = LaboratoryReportService.generate(order_id, ADMIN, self.storage)
        second = LaboratoryReportService.generate(order_id, ADMIN, self.storage)
        signed = LaboratoryReportService.signed_copy(
            order_id, ADMIN, b"%PDF-1.4\n%%EOF", "firmado.pdf", self.storage, first["id_document_version"],
        )
        self.assertEqual((1, 2, 3), (first["version"], second["version"], signed["version"]))
        with transaction_context() as db:
            versions = db.query(DocumentVersion).filter_by(id_document=first["id_document"]).order_by(DocumentVersion.version).all()
            self.assertEqual(["generated", "generated", "signed_scan"], [item.source for item in versions])
            self.assertEqual("signed", db.get(Document, first["id_document"]).status)
            for version in versions:
                self.assertTrue((Path(self.temporary.name) / version.file_path).is_file())


if __name__ == "__main__":
    unittest.main()