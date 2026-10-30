from flask import Blueprint, current_app, jsonify, request, send_file

from app.services.document_service import DocumentManagementService, SecureDocumentStorage
from app.utils.auth import require_entity_permission, token_required


bp_document_management = Blueprint("document_management", __name__, url_prefix="/document")

PREVIEWABLE_MIME_TYPES = {"application/pdf", "image/png", "image/jpeg"}


def _storage():
    return SecureDocumentStorage(current_app.config["UPLOAD_ROOT"])


@bp_document_management.get("/categories")
@token_required
@require_entity_permission("document", "read")
def categories(user_data):
    return jsonify(DocumentManagementService.categories())


@bp_document_management.get("/employees")
@token_required
@require_entity_permission("document", "read")
def employees(user_data):
    return jsonify(DocumentManagementService.employees(user_data))


@bp_document_management.get("/uploaders")
@token_required
@require_entity_permission("document", "read")
def uploaders(user_data):
    return jsonify(DocumentManagementService.uploaders(user_data))


@bp_document_management.get("/")
@token_required
@require_entity_permission("document", "read")
def list_documents(user_data):
    return jsonify(DocumentManagementService.list(user_data, request.args.get("page", 1), request.args.get("per_page", 20), request.args))


@bp_document_management.get("/<int:document_id>")
@token_required
@require_entity_permission("document", "read")
def get_document(user_data, document_id):
    return jsonify(DocumentManagementService.get(document_id, user_data))


@bp_document_management.post("/")
@token_required
@require_entity_permission("document", "create")
def create_document(user_data):
    uploaded = request.files.get("file")
    if not uploaded or not uploaded.filename:
        return jsonify({"error_key": "errors.invalid_field", "meta": {"field": "file"}}), 400
    return jsonify(DocumentManagementService.create_with_version(user_data, request.form, uploaded.read(), uploaded.filename, _storage())), 201


@bp_document_management.put("/<int:document_id>")
@token_required
@require_entity_permission("document", "update")
def update_document(user_data, document_id):
    return jsonify(DocumentManagementService.update(document_id, user_data, request.get_json() or {}))


@bp_document_management.delete("/<int:document_id>")
@token_required
@require_entity_permission("document", "delete")
def delete_document(user_data, document_id):
    DocumentManagementService.delete(document_id, user_data)
    return "", 204


@bp_document_management.post("/<int:document_id>/versions")
@token_required
@require_entity_permission("document_version", "create")
def add_document_version(user_data, document_id):
    uploaded = request.files.get("file")
    if not uploaded or not uploaded.filename:
        return jsonify({"error_key": "errors.invalid_field", "meta": {"field": "file"}}), 400
    # Esta ruta solo recibe subidas a mano. `generated` y `signed_scan` los
    # pone el sistema desde sus propios flujos (vale, laboratorio): si el cliente
    # pudiera elegirlos, cualquiera marcaria como "del sistema" -y con eso
    # impediria borrar- un documento que no lo es.
    if request.form.get("source", "uploaded") != "uploaded":
        return jsonify({"error_key": "errors.invalid_field", "meta": {"field": "source"}}), 400
    return jsonify(DocumentManagementService.add_version(document_id, user_data, uploaded.read(), uploaded.filename, _storage(), source="uploaded", status=request.form.get("status"))), 201


@bp_document_management.get("/<int:document_id>/versions/<int:version>/content")
@token_required
@require_entity_permission("document_version", "read")
def document_content(user_data, document_id, version):
    path, mime_type, filename = DocumentManagementService.content(document_id, version, user_data, _storage())
    # En linea solo lo que el navegador sabe mostrar sin ejecutar nada (PDF e
    # imagenes); el resto -DOCX- se baja siempre. `nosniff` evita que el
    # navegador reinterprete el archivo por su contenido.
    inline = request.args.get("download") != "1" and mime_type in PREVIEWABLE_MIME_TYPES
    response = send_file(path, mimetype=mime_type, as_attachment=not inline, download_name=filename)
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response