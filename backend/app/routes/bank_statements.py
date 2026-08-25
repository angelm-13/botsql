from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import func, select
from werkzeug.utils import secure_filename

from app.models import BankAccount, BankStatement, BankStatementMovement, Invoice
from app.models.session import transaction_context
from app.services.bank_statement_import import parse_bank_statement, reconcile_statement
from app.utils.auth import require_entity_permission, token_required
from app.utils.errors import AppError


bp_bank_statements = Blueprint("bank_statements", __name__, url_prefix="/bank-statements")
MAX_STATEMENT_BYTES = 10 * 1024 * 1024


def _integer(value, field):
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise AppError("errors.invalid_field", 400, {"field": field}) from exc


def _unrestricted(user_data):
    return bool(user_data.get("is_superuser") or user_data.get("is_bootstrap_admin"))


def _account_for_actor(db, account_id, user_data):
    account = db.get(BankAccount, _integer(account_id, "id_bank_account"))
    if not account or not account.id_proyect:
        raise AppError("errors.resource_not_found", 404)
    actor_project = user_data.get("id_proyect") or user_data.get("project_id")
    if not _unrestricted(user_data) and str(actor_project) != str(account.id_proyect):
        raise AppError("errors.permission_denied", 403)
    return account


def _statement_for_actor(db, statement_id, user_data):
    statement = db.get(BankStatement, _integer(statement_id, "id_bank_statement"))
    if not statement:
        raise AppError("errors.resource_not_found", 404)
    actor_project = user_data.get("id_proyect") or user_data.get("project_id")
    if not _unrestricted(user_data) and str(actor_project) != str(statement.id_proyect):
        raise AppError("errors.permission_denied", 403)
    return statement


def _json_value(value):
    if isinstance(value, Decimal):
        return float(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _preview_payload(parsed):
    reconciliation = reconcile_statement(parsed)
    statement = {key: _json_value(parsed.get(key)) for key in (
        "period_start", "period_end", "total_debits", "total_credits",
        "document_total_debits", "document_total_credits", "starting_balance",
        "ending_balance", "average_balance", "parser_name",
    )}
    movements = [{key: _json_value(value) for key, value in item.items()} for item in parsed["movements"]]
    return {
        "statement": statement,
        "movements": movements,
        "movement_count": len(movements),
        "reconciliation": reconciliation,
        "suggested_status": "completed" if reconciliation["ok"] else "requires_review",
    }


def _read_upload():
    uploaded = request.files.get("file")
    if not uploaded or not uploaded.filename:
        raise AppError("errors.invalid_field", 400, {"field": "file"})
    filename = secure_filename(uploaded.filename)
    if not filename.lower().endswith((".pdf", ".csv")):
        raise AppError("errors.invalid_field", 400, {"field": "file"})
    raw_bytes = uploaded.read()
    if not raw_bytes or len(raw_bytes) > MAX_STATEMENT_BYTES:
        raise AppError("errors.invalid_field", 400, {"field": "file", "max_mb": 10})
    try:
        return filename, raw_bytes, parse_bank_statement(raw_bytes, filename)
    except ValueError as exc:
        raise AppError("bank_statement.parse_failed", 422, {"reason": str(exc)}) from exc


@bp_bank_statements.route("/preview", methods=["POST"])
@bp_bank_statements.route("/import/preview", methods=["POST"])
@token_required
@require_entity_permission("bank_account", "update")
def preview_bank_statement(user_data):
    filename, _, parsed = _read_upload()
    with transaction_context() as db:
        account = _account_for_actor(db, request.form.get("id_bank_account"), user_data)
        duplicate = db.scalars(select(BankStatement).where(BankStatement.file_hash == parsed["file_hash"])).first()
        payload = _preview_payload(parsed)
        payload.update({
            "filename": filename,
            "id_bank_account": account.id_bank_account,
            "id_proyect": account.id_proyect,
            "already_imported": bool(duplicate),
            "duplicate_statement_id": duplicate.id_bank_statement if duplicate else None,
        })
        return jsonify(payload)


@bp_bank_statements.route("/import", methods=["POST"])
@token_required
@require_entity_permission("bank_account", "update")
def import_bank_statement(user_data):
    filename, raw_bytes, parsed = _read_upload()
    reconciliation = reconcile_statement(parsed)
    actor_id = _integer(user_data.get("id_user") or 1, "id_user")
    with transaction_context() as db:
        account = _account_for_actor(db, request.form.get("id_bank_account"), user_data)
        duplicate = db.scalars(select(BankStatement).where(BankStatement.file_hash == parsed["file_hash"])).first()
        if duplicate:
            raise AppError("errors.duplicate_resource", 409, {"id_bank_statement": duplicate.id_bank_statement})
        statement = BankStatement(
            id_bank_account=account.id_bank_account, id_proyect=account.id_proyect,
            file_hash=parsed["file_hash"], original_filename=filename,
            period_start=parsed["period_start"], period_end=parsed["period_end"],
            total_debits=parsed["total_debits"], total_credits=parsed["total_credits"],
            status="completed" if reconciliation["ok"] else "requires_review",
            starting_balance=parsed.get("starting_balance"), ending_balance=parsed.get("ending_balance"),
            average_balance=parsed.get("average_balance"), parser_name=parsed.get("parser_name"),
            extraction_confidence=Decimal("100") if reconciliation["ok"] else Decimal("80"),
            extraction_errors=reconciliation["warnings"], reconciliation_data=reconciliation,
            created_by=actor_id,
        )
        db.add(statement); db.flush()
        for item in parsed["movements"]:
            db.add(BankStatementMovement(id_bank_statement=statement.id_bank_statement, **item))
        db.flush()
        statement_id = statement.id_bank_statement
        payload = statement.serialize()
    folder = Path(current_app.config.get("UPLOAD_ROOT") or "/uploads") / "bank_statements"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"statement_{statement_id}_{filename}").write_bytes(raw_bytes)
    return jsonify({"statement": payload, "movement_count": len(parsed["movements"])}), 201


@bp_bank_statements.route("", methods=["GET"])
@bp_bank_statements.route("/", methods=["GET"])
@token_required
@require_entity_permission("bank", "read")
def list_bank_statements(user_data):
    with transaction_context() as db:
        query = db.query(BankStatement)
        actor_project = user_data.get("id_proyect") or user_data.get("project_id")
        if not _unrestricted(user_data):
            query = query.filter(BankStatement.id_proyect == _integer(actor_project, "id_proyect"))
        elif request.args.get("id_proyect"):
            query = query.filter(BankStatement.id_proyect == _integer(request.args.get("id_proyect"), "id_proyect"))
        if request.args.get("id_bank_account"):
            query = query.filter(BankStatement.id_bank_account == _integer(request.args.get("id_bank_account"), "id_bank_account"))
        rows = query.order_by(BankStatement.creation_date.desc()).all()
        items = []
        for row in rows:
            payload = row.serialize()
            payload["movement_count"] = db.query(func.count(BankStatementMovement.id_bank_statement_movement)).filter(BankStatementMovement.id_bank_statement == row.id_bank_statement).scalar()
            items.append(payload)
        return jsonify({"items": items, "total": len(items)})


@bp_bank_statements.route("/<statement_id>", methods=["GET"])
@token_required
@require_entity_permission("bank", "read")
def get_bank_statement(user_data, statement_id):
    with transaction_context() as db:
        statement = _statement_for_actor(db, statement_id, user_data)
        payload = statement.serialize()
        payload["movement_count"] = db.query(func.count(BankStatementMovement.id_bank_statement_movement)).filter(BankStatementMovement.id_bank_statement == statement.id_bank_statement).scalar()
        return jsonify(payload)


@bp_bank_statements.route("/<statement_id>/movements", methods=["GET"])
@token_required
@require_entity_permission("bank", "read")
def list_bank_statement_movements(user_data, statement_id):
    page = max(_integer(request.args.get("page") or 1, "page"), 1)
    per_page = min(max(_integer(request.args.get("per_page") or 25, "per_page"), 1), 100)
    with transaction_context() as db:
        statement = _statement_for_actor(db, statement_id, user_data)
        query = db.query(BankStatementMovement).filter(BankStatementMovement.id_bank_statement == statement.id_bank_statement)
        movement_type = str(request.args.get("type") or "").lower()
        if movement_type == "debit": query = query.filter(BankStatementMovement.debit > 0)
        if movement_type == "credit": query = query.filter(BankStatementMovement.credit > 0)
        total = query.count()
        rows = query.order_by(BankStatementMovement.sequence_number, BankStatementMovement.id_bank_statement_movement).offset((page - 1) * per_page).limit(per_page).all()
        return jsonify({"items": [row.serialize() for row in rows], "total": total, "page": page, "per_page": per_page})


@bp_bank_statements.route("/movements/<movement_id>/match", methods=["PUT"])
@token_required
@require_entity_permission("bank_account", "update")
def match_bank_statement_movement(user_data, movement_id):
    data = request.get_json(silent=True) or {}
    with transaction_context() as db:
        movement = db.get(BankStatementMovement, _integer(movement_id, "id_bank_statement_movement"))
        if not movement:
            raise AppError("errors.resource_not_found", 404)
        statement = _statement_for_actor(db, movement.id_bank_statement, user_data)
        invoice_id = data.get("id_invoice")
        if invoice_id in (None, ""):
            movement.id_invoice = None
        else:
            invoice = db.get(Invoice, _integer(invoice_id, "id_invoice"))
            if not invoice or str(invoice.id_proyect) != str(statement.id_proyect):
                raise AppError("errors.resource_not_found", 404)
            difference = abs(Decimal(movement.debit or movement.credit or 0) - Decimal(invoice.total or 0))
            if difference > Decimal("0.05") and not bool(data.get("force")):
                raise AppError("bank_statement.amount_mismatch", 409, {"difference": float(difference), "force_allowed": True})
            movement.id_invoice = invoice.id_invoice
        movement.reconciliation_note = str(data.get("note") or "")[:500] or None
        db.flush()
        return jsonify(movement.serialize())


@bp_bank_statements.route("/<statement_id>", methods=["DELETE"])
@token_required
@require_entity_permission("bank_account", "update")
def delete_bank_statement(user_data, statement_id):
    with transaction_context() as db:
        statement = _statement_for_actor(db, statement_id, user_data)
        db.query(BankStatementMovement).filter(BankStatementMovement.id_bank_statement == statement.id_bank_statement).delete(synchronize_session=False)
        db.delete(statement)
        return jsonify({"deleted": True})