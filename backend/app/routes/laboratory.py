from flask import Blueprint, current_app, jsonify, request

from app.services.document_service import SecureDocumentStorage
from app.services.laboratory_report_service import LaboratoryReportService
from app.services.laboratory_service import LaboratoryService
from app.utils.auth import require_entity_permission, token_required


bp_laboratory_equipment = Blueprint("laboratory_equipment", __name__, url_prefix="/laboratory-equipment")
bp_laboratory_service_order = Blueprint("laboratory_service_order", __name__, url_prefix="/laboratory-service-order")


@bp_laboratory_equipment.get("/")
@token_required
@require_entity_permission("laboratory_equipment", "read")
def list_equipment(user_data):
    return jsonify(LaboratoryService.list_equipment(user_data, request.args.get("page", 1), request.args.get("per_page", 20), request.args.get("search")))


@bp_laboratory_equipment.post("/")
@token_required
@require_entity_permission("laboratory_equipment", "create")
def create_equipment(user_data):
    return jsonify(LaboratoryService.create_equipment(user_data, request.get_json() or {})), 201


@bp_laboratory_service_order.get("/")
@token_required
@require_entity_permission("laboratory_service_order", "read")
def list_orders(user_data):
    return jsonify(LaboratoryService.list_orders(user_data, request.args.get("page", 1), request.args.get("per_page", 20), request.args))


@bp_laboratory_service_order.get("/<int:order_id>")
@token_required
@require_entity_permission("laboratory_service_order", "read")
def get_order(user_data, order_id):
    return jsonify(LaboratoryService.get_order(order_id, user_data))


@bp_laboratory_service_order.post("/")
@token_required
@require_entity_permission("laboratory_service_order", "create")
def create_order(user_data):
    return jsonify(LaboratoryService.create_order(user_data, request.get_json() or {})), 201


@bp_laboratory_service_order.put("/<int:order_id>/diagnosis")
@token_required
@require_entity_permission("laboratory_service_order", "update")
def update_diagnosis(user_data, order_id):
    return jsonify(LaboratoryService.update_diagnosis(order_id, user_data, request.get_json() or {}))


@bp_laboratory_service_order.post("/<int:order_id>/transition")
@token_required
@require_entity_permission("laboratory_service_order", "update")
def transition_order(user_data, order_id):
    payload = request.get_json() or {}
    return jsonify(LaboratoryService.transition(order_id, user_data, payload.get("status"), payload.get("comments")))


@bp_laboratory_service_order.get("/<int:order_id>/history")
@token_required
@require_entity_permission("laboratory_service_order_status_history", "read")
def order_history(user_data, order_id):
    return jsonify(LaboratoryService.history(order_id, user_data))


@bp_laboratory_service_order.post("/<int:order_id>/diagnostic-report")
@token_required
@require_entity_permission("laboratory_service_order", "update")
def generate_report(user_data, order_id):
    return jsonify(LaboratoryReportService.generate(order_id, user_data, SecureDocumentStorage(current_app.config["UPLOAD_ROOT"]))), 201


@bp_laboratory_service_order.post("/<int:order_id>/diagnostic-report/signed")
@token_required
@require_entity_permission("laboratory_service_order", "update")
def upload_signed_report(user_data, order_id):
    uploaded = request.files.get("file")
    if not uploaded or not uploaded.filename:
        return jsonify({"error_key": "errors.invalid_field", "meta": {"field": "file"}}), 400
    storage = SecureDocumentStorage(current_app.config["UPLOAD_ROOT"])
    return jsonify(LaboratoryReportService.signed_copy(order_id, user_data, uploaded.read(), uploaded.filename, storage, request.form.get("id_parent_document_version"))), 201