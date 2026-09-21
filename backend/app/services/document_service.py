from __future__ import annotations

import hashlib
import os
import uuid
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import and_, exists, func, or_, select

from app.models import CustomerSupplier, Document, DocumentCategory, DocumentRelation, DocumentVersion, User
from app.models.session import transaction_context
from app.utils.errors import AppError


ALLOWED_FILE_TYPES = {
    "pdf": "application/pdf",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    # Zip-based; el magic byte solo distingue "es un OOXML" de "no lo es",
    # no docx de xlsx/pptx -- la extension sigue siendo la que decide el
    # tipo real.
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
DOCUMENT_STATUSES = {"draft", "issued", "signed", "rejected", "cancelled"}
VERSION_SOURCES = {"uploaded", "generated", "signed_scan"}


def _safe_int(value, field: str) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError):
        raise AppError("errors.invalid_field", 400, {"field": field})
    if result < 1:
        raise AppError("errors.invalid_field", 400, {"field": field})
    return result


def _is_unrestricted(user_data: dict) -> bool:
    return bool(user_data.get("is_superuser") or user_data.get("is_bootstrap_admin"))


def _actor_id(user_data: dict) -> int:
    return _safe_int(user_data.get("id_user"), "id_user")


def _actor_project(user_data: dict) -> int:
    return _safe_int(user_data.get("id_proyect") or user_data.get("project_id"), "id_proyect")


def _actor_type(user_data: dict) -> str:
    return str(user_data.get("user_type") or "").strip().lower()


def _date_value(value, field: str):
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value).split("T", 1)[0])
    except ValueError:
        raise AppError("errors.invalid_field", 400, {"field": field})


class SecureDocumentStorage:
    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.max_bytes = int(os.getenv("DOCUMENT_MAX_BYTES", str(10 * 1024 * 1024)))

    @staticmethod
    def inspect(raw: bytes, original_filename: str) -> tuple[str, str]:
        extension = Path(str(original_filename or "")).suffix.lower().lstrip(".")
        if extension not in ALLOWED_FILE_TYPES:
            raise AppError("documents.invalid_file_type", 400, {"allowed": sorted(ALLOWED_FILE_TYPES)})
        detected = None
        if raw.startswith(b"%PDF-"):
            detected = "application/pdf"
        elif raw.startswith(b"\x89PNG\r\n\x1a\n"):
            detected = "image/png"
        elif raw.startswith(b"\xff\xd8\xff"):
            detected = "image/jpeg"
        elif raw.startswith(b"PK\x03\x04"):
            detected = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if detected != ALLOWED_FILE_TYPES[extension]:
            raise AppError("documents.mime_mismatch", 400, {"extension": extension})
        return extension, detected

    def validate(self, raw: bytes, original_filename: str) -> tuple[str, str]:
        if not raw or len(raw) > self.max_bytes:
            raise AppError("documents.invalid_file_size", 400, {"max_bytes": self.max_bytes})
        return self.inspect(raw, original_filename)

    def write(self, raw: bytes, project_id: int, document_id: int, version: int, extension: str, *, subfolder: str = "documents") -> str:
        relative = Path(subfolder) / str(project_id) / str(document_id) / f"v{version}-{uuid.uuid4().hex}.{extension}"
        destination = (self.root / relative).resolve()
        if self.root not in destination.parents:
            raise AppError("documents.invalid_path", 400)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        temporary.write_bytes(raw)
        temporary.replace(destination)
        return relative.as_posix()

    def resolve(self, relative_path: str) -> Path:
        candidate = (self.root / relative_path).resolve()
        if self.root not in candidate.parents or not candidate.is_file():
            raise AppError("errors.resource_not_found", 404)
        return candidate


class DocumentManagementService:
    @staticmethod
    def _scope(stmt, user_data: dict):
        if _is_unrestricted(user_data):
            return stmt
        stmt = stmt.where(Document.id_proyect == _actor_project(user_data))
        if _actor_type(user_data) in {"client", "supplier"}:
            customer_relation = exists().where(
                and_(
                    DocumentRelation.id_document == Document.id_document,
                    DocumentRelation.deletion_date.is_(None),
                    DocumentRelation.id_customer_supplier == CustomerSupplier.id_customer_supplier,
                    CustomerSupplier.id_user == _actor_id(user_data),
                    CustomerSupplier.deletion_date.is_(None),
                )
            )
            stmt = stmt.where(customer_relation)
        return stmt

    @classmethod
    def _get(cls, db, document_id: int, user_data: dict) -> Document:
        stmt = select(Document).where(Document.id_document == document_id, Document.deletion_date.is_(None))
        record = db.scalars(cls._scope(stmt, user_data)).first()
        if not record:
            raise AppError("errors.resource_not_found", 404)
        return record

    @classmethod
    def list(cls, user_data: dict, page=1, per_page=20, filters=None):
        page, per_page = max(1, int(page)), min(100, max(1, int(per_page)))
        filters = filters or {}
        with transaction_context() as db:
            stmt = select(Document).where(Document.deletion_date.is_(None))
            stmt = cls._scope(stmt, user_data)
            if filters.get("status"):
                stmt = stmt.where(Document.status == filters["status"])
            if filters.get("id_document_category"):
                stmt = stmt.where(Document.id_document_category == _safe_int(filters["id_document_category"], "id_document_category"))
            if filters.get("search"):
                pattern = f"%{str(filters['search']).strip()}%"
                stmt = stmt.where(or_(Document.title.ilike(pattern), Document.description.ilike(pattern)))
            count = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
            records = db.scalars(stmt.order_by(Document.creation_date.desc()).offset((page - 1) * per_page).limit(per_page)).all()
            return {"items": [record.serialize() for record in records], "total": count, "page": page, "per_page": per_page}

    @classmethod
    def get(cls, document_id: int, user_data: dict):
        with transaction_context() as db:
            record = cls._get(db, document_id, user_data)
            payload = record.serialize()
            payload["relations"] = [item.serialize() for item in db.scalars(select(DocumentRelation).where(DocumentRelation.id_document == record.id_document, DocumentRelation.deletion_date.is_(None))).all()]
            payload["versions"] = [item.serialize() for item in db.scalars(select(DocumentVersion).where(DocumentVersion.id_document == record.id_document, DocumentVersion.deletion_date.is_(None)).order_by(DocumentVersion.version.desc())).all()]
            for version in payload["versions"]:
                version.pop("file_path", None)
                version.pop("source_snapshot", None)
            return payload

    @staticmethod
    def categories():
        with transaction_context() as db:
            records = db.scalars(select(DocumentCategory).where(DocumentCategory.active.is_(True), DocumentCategory.deletion_date.is_(None)).order_by(DocumentCategory.name)).all()
            return [record.serialize() for record in records]

    @staticmethod
    def employees(user_data: dict):
        with transaction_context() as db:
            records = db.scalars(select(User).where(
                User.id_proyect == _actor_project(user_data),
                User.is_employee.is_(True),
                User.deletion_date.is_(None),
            ).order_by(User.full_name)).all()
            return [{"id_user": record.id_user, "full_name": record.full_name} for record in records]

    @classmethod
    def create_with_version(cls, user_data: dict, metadata: dict, raw: bytes, original_filename: str, storage: SecureDocumentStorage):
        actor_id, project_id = _actor_id(user_data), _actor_project(user_data)
        extension, mime_type = storage.validate(raw, original_filename)
        status = str(metadata.get("status") or "draft")
        if status not in DOCUMENT_STATUSES:
            raise AppError("errors.invalid_field", 400, {"field": "status"})
        category_id = _safe_int(metadata.get("id_document_category"), "id_document_category")
        relation_type = str(metadata.get("relation_type") or "").strip()
        target_fields = {key: metadata.get(key) for key in ("id_customer_supplier", "id_employee", "id_laboratory_equipment", "id_laboratory_service_order") if metadata.get(key) not in (None, "")}
        if len(target_fields) != 1 or not relation_type:
            raise AppError("documents.single_relation_required", 400)
        target_fields = {key: _safe_int(value, key) for key, value in target_fields.items()}
        expected_relation = {
            "id_customer_supplier": {"customer", "supplier"},
            "id_employee": {"employee"},
            "id_laboratory_equipment": {"equipment"},
            "id_laboratory_service_order": {"service_order"},
        }
        target_field = next(iter(target_fields))
        if relation_type not in expected_relation[target_field]:
            raise AppError("errors.invalid_field", 400, {"field": "relation_type"})
        with transaction_context() as db:
            category = db.get(DocumentCategory, category_id)
            if not category or category.deletion_date is not None or not category.active:
                raise AppError("errors.invalid_field", 400, {"field": "id_document_category"})
            if _actor_type(user_data) in {"client", "supplier"}:
                customer_id = target_fields.get("id_customer_supplier")
                customer = db.get(CustomerSupplier, customer_id) if customer_id else None
                if not customer or customer.id_user != actor_id:
                    raise AppError("errors.resource_not_found", 404)
            employee_id = target_fields.get("id_employee")
            if employee_id:
                employee = db.get(User, employee_id)
                if not employee or employee.deletion_date is not None or employee.id_proyect != project_id or not employee.is_employee:
                    raise AppError("errors.invalid_field", 400, {"field": "id_employee"})
            document = Document(
                id_proyect=project_id, id_document_category=category_id,
                title=str(metadata.get("title") or original_filename).strip()[:200],
                description=metadata.get("description"), status=status,
                issue_date=_date_value(metadata.get("issue_date"), "issue_date"),
                expiration_date=_date_value(metadata.get("expiration_date"), "expiration_date"),
                business_reference_type=metadata.get("business_reference_type"),
                business_reference_value=metadata.get("business_reference_value"), created_by=actor_id,
            )
            db.add(document); db.flush()
            db.add(DocumentRelation(id_document=document.id_document, relation_type=relation_type, created_by=actor_id, **target_fields))
            relative_path = storage.write(raw, project_id, document.id_document, 1, extension)
            version = DocumentVersion(
                id_document=document.id_document, version=1, file_path=relative_path,
                original_filename=Path(original_filename).name[:255], extension=extension, mime_type=mime_type,
                file_size=len(raw), sha256=hashlib.sha256(raw).hexdigest(), source="uploaded",
                status=status, generated_by=actor_id,
            )
            db.add(version); db.flush()
            return {"document": document.serialize(), "version": version.serialize_summary()}

    @classmethod
    def add_version(cls, document_id: int, user_data: dict, raw: bytes, original_filename: str, storage: SecureDocumentStorage, *, source="uploaded", status=None, snapshot=None, parent_version_id=None):
        if source not in VERSION_SOURCES:
            raise AppError("errors.invalid_field", 400, {"field": "source"})
        extension, mime_type = storage.validate(raw, original_filename)
        with transaction_context() as db:
            document = cls._get(db, document_id, user_data)
            db.execute(select(Document.id_document).where(Document.id_document == document.id_document).with_for_update())
            current = db.scalar(select(func.max(DocumentVersion.version)).where(DocumentVersion.id_document == document.id_document)) or 0
            version_number = current + 1
            version_status = status or document.status
            relative_path = storage.write(raw, document.id_proyect, document.id_document, version_number, extension)
            version = DocumentVersion(
                id_document=document.id_document, version=version_number, file_path=relative_path,
                original_filename=Path(original_filename).name[:255], extension=extension, mime_type=mime_type,
                file_size=len(raw), sha256=hashlib.sha256(raw).hexdigest(), source=source,
                status=version_status, source_snapshot=snapshot, id_parent_document_version=parent_version_id,
                generated_by=_actor_id(user_data),
            )
            db.add(version); db.flush()
            return version.serialize_summary()

    @classmethod
    def content(cls, document_id: int, version_number: int, user_data: dict, storage: SecureDocumentStorage):
        with transaction_context() as db:
            document = cls._get(db, document_id, user_data)
            version = db.scalars(select(DocumentVersion).where(
                DocumentVersion.id_document == document.id_document,
                DocumentVersion.version == version_number,
                DocumentVersion.deletion_date.is_(None),
            )).first()
            if not version:
                raise AppError("errors.resource_not_found", 404)
            return storage.resolve(version.file_path), version.mime_type, version.original_filename

    @classmethod
    def update(cls, document_id: int, user_data: dict, payload: dict):
        allowed = {"title", "description", "status", "issue_date", "expiration_date", "business_reference_type", "business_reference_value"}
        with transaction_context() as db:
            document = cls._get(db, document_id, user_data)
            for key, value in payload.items():
                if key in allowed:
                    if key == "status" and value not in DOCUMENT_STATUSES:
                        raise AppError("errors.invalid_field", 400, {"field": "status"})
                    setattr(document, key, _date_value(value, key) if key in {"issue_date", "expiration_date"} else value or None)
            db.flush()
            return document.serialize()

    @classmethod
    def delete(cls, document_id: int, user_data: dict):
        from datetime import datetime, timezone
        with transaction_context() as db:
            document = cls._get(db, document_id, user_data)
            document.deletion_date = datetime.now(timezone.utc).replace(tzinfo=None)
