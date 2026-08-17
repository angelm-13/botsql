from flask import Blueprint, jsonify, request
from sqlalchemy import select
from werkzeug.utils import secure_filename

from app.models import BankAccount, BankStatement, BankStatementMovement
from app.models.session import transaction_context
from app.services.bank_statement_import import parse_statement_csv
from app.utils.auth import require_entity_permission, token_required
from app.utils.errors import AppError


bp_bank_statements = Blueprint("bank_statements", __name__, url_prefix="/bank-statements")


@bp_bank_statements.route("/import", methods=["POST"])
@token_required
@require_entity_permission("bank_account", "update")
def import_bank_statement(user_data):
    uploaded = request.files.get("file")
    account_id = request.form.get("id_bank_account")
    if not uploaded or not str(uploaded.filename or "").lower().endswith(".csv"):
        raise AppError("errors.invalid_field", 400, {"field": "file"})
    parsed = parse_statement_csv(uploaded.read())
    with transaction_context() as db:
        account = db.get(BankAccount, account_id)
        if not account or not account.id_proyect:
            raise AppError("errors.resource_not_found", 404)
        actor_project = user_data.get("id_proyect") or user_data.get("project_id")
        unrestricted = bool(user_data.get("is_superuser") or user_data.get("is_bootstrap_admin"))
        if not unrestricted and str(actor_project) != str(account.id_proyect):
            raise AppError("errors.permission_denied", 403)
        duplicate = db.scalars(select(BankStatement).where(BankStatement.file_hash == parsed["file_hash"])).first()
        if duplicate:
            raise AppError("errors.duplicate_resource", 409)
        statement = BankStatement(
            id_bank_account=account.id_bank_account, id_proyect=account.id_proyect,
            file_hash=parsed["file_hash"], original_filename=secure_filename(uploaded.filename),
            period_start=parsed["period_start"], period_end=parsed["period_end"],
            total_debits=parsed["total_debits"], total_credits=parsed["total_credits"],
            status="requires_review", created_by=int(user_data.get("id_user") or 0),
        )
        db.add(statement); db.flush()
        for item in parsed["movements"]:
            db.add(BankStatementMovement(id_bank_statement=statement.id_bank_statement, **item))
        db.flush()
        return jsonify({"id_bank_statement": statement.id_bank_statement, "status": statement.status, "movement_count": len(parsed["movements"])}), 201