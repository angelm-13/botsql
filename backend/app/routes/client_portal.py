from __future__ import annotations

from flask import Blueprint, jsonify, request
from sqlalchemy import select

from app.middleware.public_jwt import require_public_jwt
from app.models import CustomerSupplier, Invoice, InvoiceMaterialService, QuotationComment
from app.models.session import transaction_context
from app.services.quotation_service import normalize_status, validate_transition
from app.utils.errors import AppError


bp_client_portal = Blueprint("client_portal", __name__, url_prefix="/public/client-portal")


def _owned_invoice(db, user_id, invoice_id):
    return db.scalars(
        select(Invoice)
        .join(CustomerSupplier, CustomerSupplier.id_customer_supplier == Invoice.id_customer_supplier)
        .where(Invoice.id_invoice == invoice_id)
        .where(CustomerSupplier.id_user == user_id)
        .where(CustomerSupplier.type == "client")
        .where(CustomerSupplier.deletion_date.is_(None))
    ).first()


def _summary(invoice):
    return {
        "id_invoice": invoice.id_invoice,
        "folio": invoice.folio,
        "date_emision": invoice.date_emision.isoformat() if invoice.date_emision else None,
        "date_expiration": invoice.date_expiration.isoformat() if invoice.date_expiration else None,
        "currency": invoice.currency,
        "subtotal": str(invoice.subtotal or "0"),
        "tax": str(invoice.tax or "0"),
        "total": str(invoice.total or "0"),
        "invoice_status": normalize_status(invoice.invoice_status),
        "commercial_terms": invoice.commercial_terms,
    }


@bp_client_portal.route("/quotations", methods=["GET"])
@require_public_jwt
def list_client_quotations(user_data):
    with transaction_context() as db:
        rows = db.scalars(
            select(Invoice)
            .join(CustomerSupplier, CustomerSupplier.id_customer_supplier == Invoice.id_customer_supplier)
            .where(CustomerSupplier.id_user == user_data["id_user"])
            .where(CustomerSupplier.type == "client")
            .where(CustomerSupplier.deletion_date.is_(None))
            .order_by(Invoice.creation_date.desc())
        ).all()
        return jsonify({"items": [_summary(row) for row in rows]})


@bp_client_portal.route("/quotations/<invoice_id>", methods=["GET"])
@require_public_jwt
def get_client_quotation(user_data, invoice_id):
    with transaction_context() as db:
        invoice = _owned_invoice(db, user_data["id_user"], invoice_id)
        if not invoice:
            raise AppError("errors.resource_not_found", 404)
        lines = db.scalars(
            select(InvoiceMaterialService).where(InvoiceMaterialService.id_invoice == invoice.id_invoice)
        ).all()
        comments = db.scalars(
            select(QuotationComment)
            .where(QuotationComment.id_invoice == invoice.id_invoice)
            .order_by(QuotationComment.creation_date.asc())
        ).all()
        return jsonify({"quotation": _summary(invoice), "lines": [line.serialize() for line in lines], "comments": [comment.serialize() for comment in comments]})


@bp_client_portal.route("/quotations/<invoice_id>/decision", methods=["POST"])
@require_public_jwt
def decide_client_quotation(user_data, invoice_id):
    decision = str((request.get_json(silent=True) or {}).get("decision") or "").lower()
    target = {"accept": "approved", "reject": "rejected"}.get(decision)
    if not target:
        raise AppError("errors.invalid_field", 400, {"field": "decision"})
    with transaction_context() as db:
        invoice = _owned_invoice(db, user_data["id_user"], invoice_id)
        if not invoice:
            raise AppError("errors.resource_not_found", 404)
        invoice.invoice_status = validate_transition(invoice.invoice_status, target)
        db.flush()
        return jsonify({"quotation": _summary(invoice)})


@bp_client_portal.route("/quotations/<invoice_id>/comments", methods=["POST"])
@require_public_jwt
def create_client_comment(user_data, invoice_id):
    message = str((request.get_json(silent=True) or {}).get("message") or "").strip()
    if not message or len(message) > 1000:
        raise AppError("errors.invalid_field", 400, {"field": "message"})
    with transaction_context() as db:
        invoice = _owned_invoice(db, user_data["id_user"], invoice_id)
        if not invoice:
            raise AppError("errors.resource_not_found", 404)
        comment = QuotationComment(id_invoice=invoice.id_invoice, id_user=user_data["id_user"], message=message)
        db.add(comment)
        db.flush()
        return jsonify(comment.serialize()), 201