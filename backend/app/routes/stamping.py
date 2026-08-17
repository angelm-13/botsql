from flask import Blueprint, jsonify, request

from app.services.stamping import stamp_invoice
from app.utils.auth import require_entity_permission, token_required


bp_stamping = Blueprint("stamping", __name__, url_prefix="/stamping")


@bp_stamping.route("/invoices/<invoice_id>", methods=["POST"])
@token_required
@require_entity_permission("invoice", "update")
def create_stamping_operation(user_data, invoice_id):
    payload = request.get_json(silent=True) or {}
    operation, created = stamp_invoice(invoice_id, payload.get("idempotency_key"), user_data)
    return jsonify({"operation": operation, "idempotent_replay": not created}), (201 if created else 200)