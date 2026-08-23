from __future__ import annotations

from flask import Blueprint, jsonify, request

from app.services.appointment_service import (
    create_appointment_type,
    create_availability_override,
    create_availability_rule,
    create_profile,
    list_appointments,
    list_profiles,
)
from app.utils.auth import require_entity_permission, token_required


bp_appointments = Blueprint("appointments", __name__, url_prefix="/appointments")


@bp_appointments.route("/profiles", methods=["GET"])
@token_required
@require_entity_permission("appointment", "read")
def get_profiles(user_data):
    return jsonify(list_profiles(user_data))


@bp_appointments.route("/profiles", methods=["POST"])
@token_required
@require_entity_permission("appointment", "create")
def post_profile(user_data):
    return jsonify(create_profile(request.get_json() or {}, user_data)), 201


@bp_appointments.route("/profiles/<int:profile_id>/types", methods=["POST"])
@token_required
@require_entity_permission("appointment", "create")
def post_appointment_type(user_data, profile_id):
    return jsonify(create_appointment_type(profile_id, request.get_json() or {}, user_data)), 201


@bp_appointments.route("/profiles/<int:profile_id>/availability-rules", methods=["POST"])
@token_required
@require_entity_permission("appointment", "create")
def post_availability_rule(user_data, profile_id):
    return jsonify(create_availability_rule(profile_id, request.get_json() or {}, user_data)), 201


@bp_appointments.route("/profiles/<int:profile_id>/availability-overrides", methods=["POST"])
@token_required
@require_entity_permission("appointment", "create")
def post_availability_override(user_data, profile_id):
    return jsonify(create_availability_override(profile_id, request.get_json() or {}, user_data)), 201


@bp_appointments.route("/", methods=["GET"])
@token_required
@require_entity_permission("appointment", "read")
def get_appointments(user_data):
    return jsonify(list_appointments(
        user_data,
        status=request.args.get("status"),
        date_from=request.args.get("date_from"),
        date_to=request.args.get("date_to"),
    ))