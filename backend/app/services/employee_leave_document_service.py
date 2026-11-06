"""La hoja de incapacidad del IMSS de una ausencia (revision contable, 2026-10-28).

La sube el propio empleado al reportar su incapacidad, o RH si se la entregaron
en papel. Se guarda con el mecanismo del modulo de Documentos -un `document`
por incapacidad (categoria `disability_certificate`, referencia
employee_leave/<id>) y una `document_version` por archivo-, igual que el vale
de almacen archiva su PDF: trae el sha256, el tamaño y el historial sin
inventar una carpeta ni una tabla.

Quien la ve: SOLO el propio empleado y RH (quien puede editar ausencias). Es un
dato medico, sensible para la ley de datos personales; el supervisor ve las
fechas de la incapacidad, nunca la hoja. Por lo mismo el modulo de Documentos
la esconde a los demas (DocumentManagementService._sin_incapacidades_ajenas).
A quien no puede verla se le responde 404, no 403: no se revela que exista.

Se aceptan foto (JPG, PNG) o PDF de hasta 10 MB (DOCUMENT_MAX_BYTES).
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from sqlalchemy import func, select

from app.models import EmployeeLeave, User
from app.models.document import Document, DocumentCategory, DocumentVersion
from app.models.session import transaction_context
from app.services.document_service import ALLOWED_FILE_TYPES, SecureDocumentStorage
from app.utils.errors import AppError

CATEGORIA = "disability_certificate"
REFERENCIA = "employee_leave"
TIPOS_DE_HOJA = {ext: ALLOWED_FILE_TYPES[ext] for ext in ("pdf", "jpg", "jpeg", "png")}


def puede_ver_todas(user_data: dict) -> bool:
    """RH: quien puede editar ausencias (la misma regla que revisa solicitudes)."""
    from app.services.employee_leave_service import _es_rh
    return bool(user_data.get("is_superuser") or user_data.get("is_bootstrap_admin") or _es_rh(user_data))


def _incapacidad(db, id_ausencia, user_data: dict) -> EmployeeLeave:
    try:
        ausencia = db.get(EmployeeLeave, int(id_ausencia))
    except (TypeError, ValueError):
        ausencia = None
    if (ausencia is None or ausencia.deletion_date is not None
            or (ausencia.id_user != user_data.get("id_user") and not puede_ver_todas(user_data))):
        raise AppError("errors.resource_not_found", 404)
    if ausencia.leave_type != "disability":
        raise AppError("errors.invalid_field", 400, {"field": "leave_type", "reason": "not_disability"})
    return ausencia


def _expediente(db, ausencia: EmployeeLeave, actor_id: int, crear: bool) -> Document | None:
    """El `document` de esta incapacidad; uno por incapacidad, las hojas son sus versiones."""
    expediente = db.scalars(
        select(Document).join(DocumentCategory, DocumentCategory.id_document_category == Document.id_document_category)
        .where(DocumentCategory.code == CATEGORIA)
        .where(Document.business_reference_type == REFERENCIA)
        .where(Document.business_reference_value == str(ausencia.id_employee_leave))
        .where(Document.deletion_date.is_(None))
    ).first()
    if expediente is not None or not crear:
        return expediente
    categoria = db.scalars(select(DocumentCategory).where(DocumentCategory.code == CATEGORIA)
                           .where(DocumentCategory.deletion_date.is_(None))).first()
    if categoria is None:
        raise AppError("documents.category_not_configured", 500, {"code": CATEGORIA})
    empleado = db.get(User, ausencia.id_user)
    # `document.id_proyect` es obligatorio: el del empleado, que es de quien es la hoja.
    if not empleado or not empleado.id_proyect:
        raise AppError("errors.resource_scope_missing", 409, {"entity": "proyect"})
    expediente = Document(
        id_proyect=empleado.id_proyect, id_document_category=categoria.id_document_category,
        title=f"Incapacidad de {empleado.full_name or empleado.id_user} del {ausencia.start_date} al {ausencia.end_date}"[:200],
        status="issued", business_reference_type=REFERENCIA,
        business_reference_value=str(ausencia.id_employee_leave), issue_date=ausencia.start_date,
        created_by=actor_id,
    )
    db.add(expediente)
    db.flush()
    return expediente


def _fila(version: DocumentVersion, nombres: dict) -> dict:
    return {"version": version.version, "original_filename": version.original_filename,
            "mime_type": version.mime_type, "file_size": version.file_size,
            "uploaded_by": version.generated_by, "uploaded_by_name": nombres.get(version.generated_by) or "",
            "creation_date": version.creation_date.isoformat() if version.creation_date else None}


def listar(id_ausencia, user_data: dict) -> list[dict]:
    with transaction_context() as db:
        ausencia = _incapacidad(db, id_ausencia, user_data)
        expediente = _expediente(db, ausencia, user_data.get("id_user"), crear=False)
        if expediente is None:
            return []
        versiones = db.scalars(select(DocumentVersion)
                               .where(DocumentVersion.id_document == expediente.id_document)
                               .where(DocumentVersion.deletion_date.is_(None))
                               .order_by(DocumentVersion.version.desc())).all()
        nombres = dict(db.execute(select(User.id_user, User.full_name)
                                  .where(User.id_user.in_([v.generated_by for v in versiones] or [0]))).all())
        return [_fila(v, nombres) for v in versiones]


def subir(id_ausencia, user_data: dict, raw: bytes, nombre: str, storage: SecureDocumentStorage) -> dict:
    """Agrega una hoja (otra version si ya habia una: nada se pisa)."""
    extension, mime = storage.validate(raw, nombre, allowed_types=TIPOS_DE_HOJA)
    actor_id = user_data.get("id_user")
    with transaction_context() as db:
        ausencia = _incapacidad(db, id_ausencia, user_data)
        expediente = _expediente(db, ausencia, actor_id, crear=True)
        db.execute(select(Document.id_document).where(Document.id_document == expediente.id_document).with_for_update())
        siguiente = (db.scalar(select(func.max(DocumentVersion.version))
                               .where(DocumentVersion.id_document == expediente.id_document)) or 0) + 1
        ruta = storage.write(raw, expediente.id_proyect, expediente.id_document, siguiente, extension)
        version = DocumentVersion(
            id_document=expediente.id_document, version=siguiente, file_path=ruta,
            original_filename=Path(nombre).name[:255], extension=extension, mime_type=mime,
            file_size=len(raw), sha256=hashlib.sha256(raw).hexdigest(), source="uploaded",
            status="issued", generated_by=actor_id,
        )
        db.add(version)
        db.flush()
        nombre_actor = db.scalar(select(User.full_name).where(User.id_user == actor_id))
        return _fila(version, {actor_id: nombre_actor})


def contenido(id_ausencia, numero, user_data: dict, storage: SecureDocumentStorage):
    """(ruta, mime, nombre) de una hoja, para mandarla al navegador."""
    with transaction_context() as db:
        ausencia = _incapacidad(db, id_ausencia, user_data)
        expediente = _expediente(db, ausencia, user_data.get("id_user"), crear=False)
        version = None if expediente is None else db.scalars(
            select(DocumentVersion).where(DocumentVersion.id_document == expediente.id_document)
            .where(DocumentVersion.version == int(numero)).where(DocumentVersion.deletion_date.is_(None))).first()
        if version is None:
            raise AppError("errors.resource_not_found", 404)
        return storage.resolve(version.file_path), version.mime_type, version.original_filename
