
from __future__ import annotations

from flask import Blueprint, jsonify, request
from sqlalchemy import select

from app.models.session import transaction_context
from app.models.entity_permission import EntityPermission
from app.models.audit_log import AuditLog
from app.security.permissions import PermissionAction, has_permission
from app.utils.auth import token_required

bp_security = Blueprint("security", __name__, url_prefix="/security")

KNOWN_ENTITIES = [
  "bank",
  "bank_account",
  "brand",
  "customer_supplier",
  "department",
  "entity_permission",
  "event_log",
  "field",
  "fiscal_account",
  "fiscal_record",
  "fiscal_stamp",
  "incident",
  "incident_detail",
  "incident_type",
  "inventory_status",
  "invoice",
  "invoice_material_service",
  "level",
  "location",
  "location_type",
  "material",
  "material_component",
  "movement",
  "nm_field_permission",
  "nm_incident_product",
  "nm_survey_user",
  "nm_template_task",
  "password_reset_token",
  "payroll_concept",
  "payroll_detail",
  "payroll_movement",
  "payroll_period",
  "permission",
  "product",
  "product_family",
  "product_sale_config",
  "proyect",
  "public_api_key",
  "service",
  "status",
  "subdepartment",
  "survey_multiple_answer",
  "survey_question",
  "task",
  "task_note",
  "task_type",
  "template",
  "theme",
  "ticket",
  "unit",
  "user",
  "user_mfa"
]


@bp_security.route("/entities", methods=["GET"])
@token_required
def list_security_entities(user_data):
    return jsonify({"items": KNOWN_ENTITIES})


@bp_security.route("/me/permissions", methods=["GET"])
@token_required
def my_permissions(user_data):
    permission_id = user_data.get("id_permission")
    with transaction_context() as db_session:
        rows = db_session.scalars(
            select(EntityPermission).where(
                EntityPermission.id_permission == permission_id,
                EntityPermission.deletion_date.is_(None),
            )
        ).all()
        return jsonify({"items": [row.serialize() for row in rows]})


@bp_security.route("/check", methods=["POST"])
@token_required
def check_permission(user_data):
    data = request.get_json() or {}
    entity = data.get("entity_name")
    action = str(data.get("action") or "read").upper()
    action_map = {"CREATE": PermissionAction.CREATE, "READ": PermissionAction.READ, "UPDATE": PermissionAction.UPDATE, "DELETE": PermissionAction.DELETE}
    if entity not in KNOWN_ENTITIES or action not in action_map:
        return jsonify({"allowed": False, "message_key": "security.permission.invalid_scope"}), 400
    with transaction_context() as db_session:
        allowed = has_permission(db_session, user_data, entity, action_map[action])
        return jsonify({"allowed": allowed, "entity_name": entity, "action": action.lower()})


@bp_security.route("/audit", methods=["GET"])
@token_required
def list_audit(user_data):
    page = int(request.args.get("page", 1))
    per_page = min(int(request.args.get("per_page", 25)), 100)
    with transaction_context() as db_session:
        rows = db_session.scalars(
            select(AuditLog)
            .order_by(AuditLog.creation_date.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        ).all()
        return jsonify({"items": [row.serialize() for row in rows], "page": page, "per_page": per_page})
