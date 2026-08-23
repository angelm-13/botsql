from flask import Blueprint, jsonify, request

from app.services.pac_config_service import get_config, provider_credentials, save_config
from app.services.stamping import FacturamaSandboxProvider, stamp_invoice
from app.utils.errors import AppError
from app.utils.auth import require_entity_permission, token_required


bp_stamping = Blueprint("stamping", __name__, url_prefix="/stamping")


def _require_admin(user_data):
    if not (user_data.get("is_superuser") or user_data.get("is_bootstrap_admin") or str(user_data.get("user_type") or "").lower() == "admin"):
        raise AppError("errors.permission_denied", 403)


@bp_stamping.route("/config", methods=["GET"])
@token_required
def read_stamping_config(user_data):
    _require_admin(user_data)
    return jsonify(get_config())


@bp_stamping.route("/config", methods=["PUT"])
@token_required
def update_stamping_config(user_data):
    _require_admin(user_data)
    return jsonify(save_config(request.get_json(silent=True) or {}))


@bp_stamping.route("/config/test", methods=["POST"])
@token_required
def test_stamping_config(user_data):
    _require_admin(user_data)
    credentials = provider_credentials(request.get_json(silent=True) or {})
    if credentials["provider"] == "fake":
        return jsonify({"ok": True, "message": "Modo simulado activo, sin validez fiscal."})
    provider = FacturamaSandboxProvider(
        base_url=credentials["base_url"], username=credentials["username"], password=credentials["password"],
        expedition_place=credentials["expedition_place"], name_id=credentials["name_id"],
    )
    ok, message = provider.test_connection()
    return jsonify({"ok": ok, "message": message})


@bp_stamping.route("/invoices/<invoice_id>", methods=["POST"])
@token_required
@require_entity_permission("invoice", "update")
def create_stamping_operation(user_data, invoice_id):
    payload = request.get_json(silent=True) or {}
    operation, created = stamp_invoice(invoice_id, payload.get("idempotency_key"), user_data)
    return jsonify({"operation": operation, "idempotent_replay": not created}), (201 if created else 200)