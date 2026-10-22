from __future__ import annotations

import hashlib
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func, select

from app.models import CustomerSupplier, Document, DocumentCategory, DocumentRelation, DocumentVersion, LaboratoryEquipment, User
from app.models.session import transaction_context
from app.services.document_service import DocumentManagementService, SecureDocumentStorage, _actor_id
from app.services.laboratory_service import LaboratoryService
from app.utils.errors import AppError


class LaboratoryReportService:
    @staticmethod
    def _document_renderer():
        app_path = os.getenv("DOCUMENTS_REPORTS_APP_PATH", "/documents-reports/app")
        if app_path not in sys.path:
            sys.path.insert(0, app_path)
        from documents.manifest import DOCUMENTS
        from documents.service import DocumentService
        DOCUMENTS.setdefault("laboratory_diagnostic_report", {"entity": "laboratory_service_order", "fields": []})
        return DocumentService(os.getenv("DOCUMENTS_TEMPLATES_DIR", "/documents-reports/templates"))

    @staticmethod
    def _logo_uri(path_value, storage_root: Path) -> str:
        value = str(path_value or "").strip().replace("\\", "/")
        if not value:
            return ""
        # Solo archivos dentro del almacen: el logo es texto libre (ver `_doc_logo_uri`).
        root = Path(storage_root).resolve()
        candidate = (root / value.lstrip("/").removeprefix("uploads/")).resolve()
        return candidate.as_uri() if candidate.is_relative_to(root) and candidate.is_file() else ""

    @classmethod
    def snapshot(cls, order_id: int, user_data: dict, storage_root: Path) -> dict:
        with transaction_context() as db:
            order = LaboratoryService._order(db, order_id, user_data)
            equipment = db.get(LaboratoryEquipment, order.id_laboratory_equipment)
            customer = db.get(CustomerSupplier, order.id_customer_supplier)
            technician = db.get(User, order.id_technician) if order.id_technician else None
            company = db.scalars(
                select(CustomerSupplier).join(User, User.id_user == CustomerSupplier.id_user).where(
                    User.id_proyect == order.id_proyect, CustomerSupplier.is_principal.is_(True),
                    CustomerSupplier.deletion_date.is_(None),
                )
            ).first()
            return {
                "order_id": order.id_laboratory_service_order,
                "folio": order.folio,
                "reception_date": order.reception_date.isoformat() if order.reception_date else None,
                "diagnosis_date": order.diagnosis_date.isoformat() if order.diagnosis_date else None,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "company": {
                    "name": company.name if company else "Tyakxa", "tax_id": company.tax_id if company else None,
                    "address": ", ".join(filter(None, [company.street if company else None, company.city if company else None, company.geographic_state if company else None, company.postal_code if company else None])),
                    "phone": company.phone if company else None, "email": company.email if company else None,
                    "logo_uri": cls._logo_uri(company.path_logo if company else None, storage_root),
                },
                "customer": {"name": customer.name, "contact_name": order.contact_name, "email": order.contact_email, "phone": order.contact_phone},
                "equipment": {"type": equipment.equipment_type, "brand": equipment.brand, "model": equipment.model, "serial_number": equipment.serial_number},
                "delivered_accessories": order.delivered_accessories, "reception_condition": order.reception_condition,
                "reported_failure": order.reported_failure, "technical_diagnosis": order.technical_diagnosis,
                "recommended_repair": order.recommended_repair,
                "estimated_budget": float(order.estimated_budget) if order.estimated_budget is not None else None,
                "estimated_repair_time": order.estimated_repair_time, "observations": order.observations,
                "service_conditions": order.service_conditions,
                "technician_name": technician.full_name if technician else None,
            }

    @staticmethod
    def _document_for_order(db, order, actor_id: int) -> Document:
        category = db.scalars(select(DocumentCategory).where(DocumentCategory.code == "diagnostic_report", DocumentCategory.deletion_date.is_(None))).first()
        if not category:
            raise AppError("documents.category_not_configured", 500)
        document = db.scalars(
            select(Document).join(DocumentRelation, DocumentRelation.id_document == Document.id_document).where(
                DocumentRelation.id_laboratory_service_order == order.id_laboratory_service_order,
                DocumentRelation.deletion_date.is_(None), Document.id_document_category == category.id_document_category,
                Document.deletion_date.is_(None),
            ).with_for_update()
        ).first()
        if document:
            return document
        document = Document(
            id_proyect=order.id_proyect, id_document_category=category.id_document_category,
            title=f"Reporte de diagnostico {order.folio}", status="issued",
            business_reference_type="laboratory_service_order", business_reference_value=str(order.id_laboratory_service_order),
            issue_date=datetime.now(timezone.utc).date(), created_by=actor_id,
        )
        db.add(document); db.flush()
        for relation_type, values in (
            ("customer", {"id_customer_supplier": order.id_customer_supplier}),
            ("equipment", {"id_laboratory_equipment": order.id_laboratory_equipment}),
            ("service_order", {"id_laboratory_service_order": order.id_laboratory_service_order}),
        ):
            db.add(DocumentRelation(id_document=document.id_document, relation_type=relation_type, created_by=actor_id, **values))
        db.flush()
        return document

    @classmethod
    def generate(cls, order_id: int, user_data: dict, storage: SecureDocumentStorage):
        snapshot = cls.snapshot(order_id, user_data, storage.root)
        if not snapshot.get("technical_diagnosis"):
            raise AppError("laboratory.diagnosis_required", 409)
        pdf = cls._document_renderer().render_pdf_bytes("laboratory_diagnostic_report", snapshot, "es")
        actor_id = _actor_id(user_data)
        with transaction_context() as db:
            order = LaboratoryService._order(db, order_id, user_data)
            document = cls._document_for_order(db, order, actor_id)
            db.execute(select(Document.id_document).where(Document.id_document == document.id_document).with_for_update())
            version_number = (db.scalar(select(func.max(DocumentVersion.version)).where(DocumentVersion.id_document == document.id_document)) or 0) + 1
            relative_path = storage.write(pdf, order.id_proyect, document.id_document, version_number, "pdf")
            version = DocumentVersion(
                id_document=document.id_document, version=version_number, file_path=relative_path,
                original_filename=f"diagnostico-{order.folio}-v{version_number}.pdf", extension="pdf", mime_type="application/pdf",
                file_size=len(pdf), sha256=hashlib.sha256(pdf).hexdigest(), source="generated", status="issued",
                source_snapshot=snapshot, generated_by=actor_id,
            )
            db.add(version); db.flush()
            return {"id_document": document.id_document, "version": version_number, "id_document_version": version.id_document_version}

    @classmethod
    def signed_copy(cls, order_id: int, user_data: dict, raw: bytes, filename: str, storage: SecureDocumentStorage, parent_version_id=None):
        with transaction_context() as db:
            order = LaboratoryService._order(db, order_id, user_data)
            document = cls._document_for_order(db, order, _actor_id(user_data))
            document_id = document.id_document
        result = DocumentManagementService.add_version(
            document_id, user_data, raw, filename, storage, source="signed_scan", status="signed",
            parent_version_id=int(parent_version_id) if parent_version_id else None,
        )
        with transaction_context() as db:
            db.get(Document, document_id).status = "signed"
        return result