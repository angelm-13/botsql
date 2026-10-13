from __future__ import annotations

import hashlib
import os
import uuid
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import and_, exists, func, or_, select

from app.models import (
    CustomerSupplier, Document, DocumentCategory, DocumentRelation, DocumentVersion,
    LaboratoryEquipment, LaboratoryServiceOrder, User,
)
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
# Adjuntos de PROYECTO solamente (add_project_document). No se agregan aqui
# a ALLOWED_FILE_TYPES porque esa lista tambien protege documentos
# genericos, laboratorio y vales de almacen -- ampliarla ahi los afectaria a
# los tres. Los usuarios de proyecto suben planos y CAD (.dxf/.dwg/.step)
# ademas de hojas de calculo, que esos otros modulos no necesitan.
PROJECT_ATTACHMENT_FILE_TYPES = {
    **ALLOWED_FILE_TYPES,
    "dxf": "image/vnd.dxf",
    "dwg": "application/acad",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "xls": "application/vnd.ms-excel",
    "step": "application/step",
    "stp": "application/step",
}
DOCUMENT_STATUSES = {"draft", "issued", "signed", "rejected", "cancelled"}
VERSION_SOURCES = {"uploaded", "generated", "signed_scan"}
# Un documento lo genero el sistema -vale de almacen, reporte de diagnostico y
# su copia firmada- cuando alguna de sus versiones no es una subida a mano. Se
# decide por la version y no por la categoria: la categoria la puede elegir
# cualquiera al subir un archivo, el origen de la version no.
SYSTEM_VERSION_SOURCES = ("generated", "signed_scan")


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
    def inspect(raw: bytes, original_filename: str, allowed_types: dict[str, str] | None = None) -> tuple[str, str]:
        types = allowed_types if allowed_types is not None else ALLOWED_FILE_TYPES
        extension = Path(str(original_filename or "")).suffix.lower().lstrip(".")
        if extension not in types:
            raise AppError("documents.invalid_file_type", 400, {"allowed": sorted(types)})
        expected = types[extension]
        detected = None
        if raw.startswith(b"%PDF-"):
            detected = "application/pdf"
        elif raw.startswith(b"\x89PNG\r\n\x1a\n"):
            detected = "image/png"
        elif raw.startswith(b"\xff\xd8\xff"):
            detected = "image/jpeg"
        elif raw.startswith(b"PK\x03\x04"):
            # Zip-based (docx/xlsx/pptx); el magic byte solo distingue "es un
            # OOXML" de "no lo es" -- la extension sigue siendo la que decide
            # el tipo real, igual que ya hacia docx.
            detected = expected if expected in (
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ) else None
        elif raw.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
            # OLE2 (compound file binario): xls viejo, igual que docx/xlsx
            # no distingue del resto de formatos OLE2 (doc, ppt) -- la
            # extension decide.
            detected = "application/vnd.ms-excel" if expected == "application/vnd.ms-excel" else None
        elif extension == "dwg" and raw[:3] == b"AC1":
            detected = expected
        elif extension in ("dxf", "step", "stp"):
            # Sin magic number binario (son texto plano): se valida
            # contenido en vez de un byte fijo -- un DXF real trae "SECTION"
            # cerca del inicio, un STEP real empieza con el encabezado ISO.
            texto = None
            try:
                texto = raw[:4096].decode("utf-8")
            except UnicodeDecodeError:
                try:
                    texto = raw[:4096].decode("latin-1")
                except UnicodeDecodeError:
                    texto = None
            if texto is not None:
                if extension == "dxf" and "SECTION" in texto:
                    detected = expected
                elif extension in ("step", "stp") and texto.lstrip("﻿ \t\r\n").startswith("ISO-10303-21"):
                    detected = expected
        if detected != expected:
            raise AppError("documents.mime_mismatch", 400, {"extension": extension})
        return extension, detected

    def validate(self, raw: bytes, original_filename: str, allowed_types: dict[str, str] | None = None) -> tuple[str, str]:
        if not raw or len(raw) > self.max_bytes:
            raise AppError("documents.invalid_file_size", 400, {"max_bytes": self.max_bytes})
        return self.inspect(raw, original_filename, allowed_types=allowed_types)

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
    def _sin_vales_ajenos(stmt, user_data: dict):
        """El PDF de un vale archivado como documento sigue el alcance del vale.

        Se archiva con `created_by` de quien lo bajo primero y sin dueno propio,
        asi que el alcance de `document` no sirve: quien no opera el almacen solo
        ve el expediente de un vale que es suyo (ver `_del_solicitante`).
        """
        from sqlalchemy import false, String, cast

        from app.models.incident import Incident
        from app.services.warehouse_voucher_service import _del_solicitante, _ve_todo_el_almacen

        with transaction_context() as db:
            if _ve_todo_el_almacen(db, user_data):
                return stmt
            try:
                suyos = select(cast(Incident.id_incident, String)).where(_del_solicitante(db, user_data))
                ver = and_(Document.business_reference_type == "incident",
                           Document.business_reference_value.in_(suyos))
            except AppError:
                ver = false()
        es_vale = exists().where(and_(
            DocumentCategory.id_document_category == Document.id_document_category,
            DocumentCategory.code == "warehouse_voucher",
        ))
        return stmt.where(or_(~es_vale, ver))

    @staticmethod
    def _scope(stmt, user_data: dict):
        if _is_unrestricted(user_data):
            return stmt
        stmt = stmt.where(Document.id_proyect == _actor_project(user_data))
        stmt = DocumentManagementService._sin_vales_ajenos(stmt, user_data)
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
            stmt = cls._filter_by_person(stmt, filters)
            if filters.get("created_by"):
                stmt = stmt.where(Document.created_by == _safe_int(filters["created_by"], "created_by"))
            for field, column, operator in (
                ("issue_date_from", Document.issue_date, "ge"), ("issue_date_to", Document.issue_date, "le"),
                ("expiration_date_from", Document.expiration_date, "ge"), ("expiration_date_to", Document.expiration_date, "le"),
            ):
                value = _date_value(filters.get(field), field)
                if value is not None:
                    stmt = stmt.where(column >= value if operator == "ge" else column <= value)
            count = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
            records = db.scalars(stmt.order_by(Document.creation_date.desc(), Document.id_document.desc()).offset((page - 1) * per_page).limit(per_page)).all()
            return {"items": cls._enrich(db, records), "total": count, "page": page, "per_page": per_page}

    @staticmethod
    def _filter_by_person(stmt, filters):
        """Persona = a quien esta ligado el documento (empleado o cliente/proveedor).

        Va por `document_relation`, igual que el alcance del cliente: un
        documento que no esta ligado a nadie -el PDF de un vale- no sale al
        filtrar por persona, y eso es lo correcto.
        """
        for field, column in (("id_employee", DocumentRelation.id_employee), ("id_customer_supplier", DocumentRelation.id_customer_supplier)):
            if filters.get(field):
                target = _safe_int(filters[field], field)
                stmt = stmt.where(exists().where(and_(
                    DocumentRelation.id_document == Document.id_document,
                    DocumentRelation.deletion_date.is_(None),
                    column == target,
                )))
        return stmt

    @staticmethod
    def generated_by_system():
        """Condicion SQL: alguna version viva del documento no fue subida a mano."""
        return exists().where(and_(
            DocumentVersion.id_document == Document.id_document,
            DocumentVersion.deletion_date.is_(None),
            DocumentVersion.source.in_(SYSTEM_VERSION_SOURCES),
        ))

    @classmethod
    def _enrich(cls, db, records) -> list[dict]:
        """La ficha del documento con lo que la pantalla necesita para pintar.

        Un numero fijo de consultas por pagina, no una por fila: las ligas, y
        despues categorias, personas, clientes, equipos y ordenes en bloque,
        mas cuales documentos genero el sistema.
        """
        if not records:
            return []
        ids = [record.id_document for record in records]
        relations = db.scalars(select(DocumentRelation).where(
            DocumentRelation.id_document.in_(ids), DocumentRelation.deletion_date.is_(None),
        ).order_by(DocumentRelation.id_document_relation)).all()

        categories = {item.id_document_category: item for item in db.scalars(select(DocumentCategory).where(
            DocumentCategory.id_document_category.in_({record.id_document_category for record in records}))).all()}
        user_ids = {record.created_by for record in records} | {item.id_employee for item in relations if item.id_employee}
        users = {item.id_user: item.full_name for item in db.scalars(select(User).where(User.id_user.in_(user_ids))).all()}
        customer_ids = {item.id_customer_supplier for item in relations if item.id_customer_supplier}
        customers = {item.id_customer_supplier: item.name for item in db.scalars(select(CustomerSupplier).where(
            CustomerSupplier.id_customer_supplier.in_(customer_ids))).all()} if customer_ids else {}
        equipment_ids = {item.id_laboratory_equipment for item in relations if item.id_laboratory_equipment}
        equipment = {
            item.id_laboratory_equipment: " ".join(str(part) for part in (item.equipment_type, item.brand, item.model, item.serial_number) if part)
            for item in db.scalars(select(LaboratoryEquipment).where(LaboratoryEquipment.id_laboratory_equipment.in_(equipment_ids))).all()
        } if equipment_ids else {}
        order_ids = {item.id_laboratory_service_order for item in relations if item.id_laboratory_service_order}
        orders = {item.id_laboratory_service_order: item.folio for item in db.scalars(select(LaboratoryServiceOrder).where(
            LaboratoryServiceOrder.id_laboratory_service_order.in_(order_ids))).all()} if order_ids else {}
        generated = set(db.scalars(select(Document.id_document).where(
            Document.id_document.in_(ids), cls.generated_by_system())).all())

        related: dict[int, list[dict]] = {}
        for item in relations:
            if item.id_employee:
                target = {"target": "employee", "id": item.id_employee, "name": users.get(item.id_employee)}
            elif item.id_customer_supplier:
                target = {"target": "customer_supplier", "id": item.id_customer_supplier, "name": customers.get(item.id_customer_supplier)}
            elif item.id_laboratory_equipment:
                target = {"target": "equipment", "id": item.id_laboratory_equipment, "name": equipment.get(item.id_laboratory_equipment)}
            else:
                target = {"target": "service_order", "id": item.id_laboratory_service_order, "name": orders.get(item.id_laboratory_service_order)}
            related.setdefault(item.id_document, []).append({"relation_type": item.relation_type, **target})

        items = []
        for record in records:
            payload = record.serialize()
            category = categories.get(record.id_document_category)
            payload["category_code"] = category.code if category else None
            payload["category_name"] = category.name if category else None
            payload["created_by_name"] = users.get(record.created_by)
            payload["related"] = related.get(record.id_document, [])
            payload["system_generated"] = record.id_document in generated
            items.append(payload)
        return items

    @classmethod
    def get(cls, document_id: int, user_data: dict):
        with transaction_context() as db:
            record = cls._get(db, document_id, user_data)
            payload = cls._enrich(db, [record])[0]
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
    def uploaders(cls, user_data: dict):
        """Quienes han subido algun documento que el actor puede ver (filtro "Subido por")."""
        with transaction_context() as db:
            visibles = cls._scope(select(Document.created_by).where(Document.deletion_date.is_(None)), user_data)
            records = db.scalars(select(User).where(User.id_user.in_(visibles.distinct())).order_by(User.full_name)).all()
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
            # El PDF del vale y el reporte de diagnostico son el expediente de
            # algo que sigue vivo: borrarlos deja al vale o a la orden sin su
            # historial (laboratorio, de hecho, abriria un documento nuevo desde
            # cero). El permiso de borrar no basta, ni siquiera el del admin.
            if db.scalar(select(Document.id_document).where(
                    Document.id_document == document.id_document, cls.generated_by_system())) is not None:
                raise AppError("documents.system_generated_not_deletable", 409)
            document.deletion_date = datetime.now(timezone.utc).replace(tzinfo=None)
