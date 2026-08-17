from __future__ import annotations

from sqlalchemy import select

from app.models.inventory_ledger import InventoryLedger
from app.models.invoice import Invoice
from app.models.product import Product
from app.models.session import transaction_context
from app.utils.errors import AppError


MOVEMENT_SIGNS = {
    "receive": 1,
    "return": 1,
    "loan": -1,
    "issue": -1,
    "damage": -1,
    "destroy": -1,
    "loss": -1,
}


def _integer_quantity(value, field="quantity"):
    if isinstance(value, bool):
        raise AppError("errors.invalid_field", 400, {"field": field})
    try:
        quantity = int(value)
    except (TypeError, ValueError) as exc:
        raise AppError("errors.invalid_field", 400, {"field": field}) from exc
    if quantity <= 0:
        raise AppError("errors.invalid_field", 400, {"field": field})
    return quantity


def _actor_project_id(user_data):
    value = user_data.get("id_proyect") or user_data.get("project_id")
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def apply_inventory_movement(product_id, payload, user_data):
    movement_type = str(payload.get("movement_type") or "").strip().lower()
    if movement_type not in {*MOVEMENT_SIGNS, "adjustment"}:
        raise AppError("errors.invalid_field", 400, {"field": "movement_type"})

    idempotency_key = str(payload.get("idempotency_key") or "").strip()
    if not idempotency_key or len(idempotency_key) > 100:
        raise AppError("errors.invalid_field", 400, {"field": "idempotency_key"})

    if movement_type == "adjustment":
        try:
            quantity_delta = int(payload.get("quantity_delta"))
        except (TypeError, ValueError) as exc:
            raise AppError("errors.invalid_field", 400, {"field": "quantity_delta"}) from exc
        if quantity_delta == 0:
            raise AppError("errors.invalid_field", 400, {"field": "quantity_delta"})
    else:
        quantity_delta = MOVEMENT_SIGNS[movement_type] * _integer_quantity(payload.get("quantity"))

    with transaction_context() as db:
        previous = db.scalars(
            select(InventoryLedger).where(InventoryLedger.idempotency_key == idempotency_key)
        ).first()
        if previous:
            if previous.id_product != int(product_id):
                raise AppError("errors.idempotency_conflict", 409)
            return previous.serialize(), False

        product = db.scalars(
            select(Product).where(Product.id_product == product_id).with_for_update()
        ).first()
        if not product:
            raise AppError("errors.not_found", 404, {"entity": "product"})

        invoice = db.get(Invoice, product.id_invoice)
        project_id = getattr(invoice, "id_proyect", None)
        actor_project_id = _actor_project_id(user_data)
        unrestricted = bool(user_data.get("is_superuser") or user_data.get("is_bootstrap_admin"))
        if not project_id:
            raise AppError("errors.resource_scope_missing", 409)
        if not unrestricted and actor_project_id != project_id:
            raise AppError("errors.permission_denied", 403)

        current_balance = int(product.cantidad or 0)
        new_balance = current_balance + quantity_delta
        if new_balance < 0:
            raise AppError("errors.inventory_insufficient_stock", 409, {"available": current_balance})

        product.cantidad = new_balance
        ledger = InventoryLedger(
            id_product=product.id_product,
            id_proyect=project_id,
            movement_type=movement_type,
            quantity_delta=quantity_delta,
            balance_after=new_balance,
            idempotency_key=idempotency_key,
            reference_type=str(payload.get("reference_type") or "").strip()[:50] or None,
            reference_id=str(payload.get("reference_id") or "").strip()[:100] or None,
            reason=str(payload.get("reason") or "").strip()[:250] or None,
            created_by=int(user_data.get("id_user") or 0),
        )
        db.add(ledger)
        db.flush()
        return ledger.serialize(), True