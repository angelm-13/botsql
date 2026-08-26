"""Movimientos de almacen sobre el libro de inventario.

`inventory_ledger` es un libro de solo agregado: cada movimiento queda con su
delta, el saldo resultante y quien lo hizo. El saldo vivo se guarda en
`product.cantidad` y se protege con un bloqueo de fila, de modo que dos
movimientos concurrentes no puedan dejar existencias en negativo.
"""

from __future__ import annotations

from sqlalchemy import func, select

from app.models.inventory_ledger import InventoryLedger
from app.models.invoice import Invoice
from app.models.product import Product
from app.models.session import transaction_context
from app.utils.errors import AppError


# Signo que cada tipo de movimiento aplica al saldo.
MOVEMENT_SIGNS = {
    "receive": 1,
    "return": 1,
    "loan": -1,
    "issue": -1,
    "damage": -1,
    "destroy": -1,
    "loss": -1,
}

# Un ajuste no responde a una operacion del negocio, asi que solo se acepta
# con una justificacion: es la unica forma de auditar por que cambio el saldo.
REASON_REQUIRED_MOVEMENTS = {"adjustment", "damage", "destroy", "loss"}

# Origen del movimiento. Se acota para que el libro sea consultable y no una
# bolsa de texto libre.
REFERENCE_TYPES = {
    "invoice",
    "invoice_line",
    "purchase",
    "project",
    "task",
    "incident",
    "count",
    "manual",
}

MOVEMENT_TYPES = frozenset({*MOVEMENT_SIGNS, "adjustment"})


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


def _require_project_scope(product_project_id, user_data):
    unrestricted = bool(user_data.get("is_superuser") or user_data.get("is_bootstrap_admin"))
    if not product_project_id:
        raise AppError("errors.resource_scope_missing", 409)
    if not unrestricted and _actor_project_id(user_data) != product_project_id:
        raise AppError("errors.permission_denied", 403)


def _product_project_id(db, product):
    invoice = db.get(Invoice, product.id_invoice)
    return getattr(invoice, "id_proyect", None)


def _reference(payload):
    reference_type = str(payload.get("reference_type") or "").strip().lower() or None
    if reference_type and reference_type not in REFERENCE_TYPES:
        raise AppError(
            "errors.invalid_field",
            400,
            {"field": "reference_type", "allowed": sorted(REFERENCE_TYPES)},
        )
    return reference_type, str(payload.get("reference_id") or "").strip()[:100] or None


def apply_inventory_movement(product_id, payload, user_data):
    movement_type = str(payload.get("movement_type") or "").strip().lower()
    if movement_type not in MOVEMENT_TYPES:
        raise AppError("errors.invalid_field", 400, {"field": "movement_type", "allowed": sorted(MOVEMENT_TYPES)})

    idempotency_key = str(payload.get("idempotency_key") or "").strip()
    if not idempotency_key or len(idempotency_key) > 100:
        raise AppError("errors.invalid_field", 400, {"field": "idempotency_key"})

    reason = str(payload.get("reason") or "").strip()[:250]
    if movement_type in REASON_REQUIRED_MOVEMENTS and not reason:
        raise AppError("errors.inventory_reason_required", 400, {"field": "reason", "movement_type": movement_type})

    reference_type, reference_id = _reference(payload)

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

        project_id = _product_project_id(db, product)
        _require_project_scope(project_id, user_data)

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
            reference_type=reference_type,
            reference_id=reference_id,
            reason=reason or None,
            created_by=int(user_data.get("id_user") or 0),
        )
        db.add(ledger)
        db.flush()
        return ledger.serialize(), True


def list_inventory_movements(product_id, user_data, *, page=1, per_page=50, movement_type=None):
    """Historial de movimientos de un producto, del mas reciente al mas viejo.

    Sin esta consulta el libro no era auditable: se escribia pero no habia
    forma de revisar por que un saldo llego a donde esta.
    """
    try:
        page = max(int(page or 1), 1)
        per_page = min(max(int(per_page or 50), 1), 200)
    except (TypeError, ValueError) as exc:
        raise AppError("errors.invalid_field", 400, {"field": "page"}) from exc

    normalized_type = str(movement_type or "").strip().lower() or None
    if normalized_type and normalized_type not in MOVEMENT_TYPES:
        raise AppError("errors.invalid_field", 400, {"field": "movement_type"})

    with transaction_context() as db:
        product = db.get(Product, product_id)
        if not product:
            raise AppError("errors.not_found", 404, {"entity": "product"})
        _require_project_scope(_product_project_id(db, product), user_data)

        query = select(InventoryLedger).where(InventoryLedger.id_product == product.id_product)
        if normalized_type:
            query = query.where(InventoryLedger.movement_type == normalized_type)
        total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
        rows = db.scalars(
            query.order_by(InventoryLedger.id_inventory_ledger.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        ).all()
        return {
            "items": [row.serialize() for row in rows],
            "page": page,
            "per_page": per_page,
            "total": total,
            "balance": int(product.cantidad or 0),
        }


def reconcile_product_stock(product_id, user_data) -> dict:
    """Compara el saldo vivo del producto contra la suma del libro.

    Si no coinciden, el saldo se movio por fuera de `apply_inventory_movement`
    (una edicion directa de `product.cantidad`, por ejemplo) y el inventario
    dejo de ser confiable.
    """
    with transaction_context() as db:
        product = db.get(Product, product_id)
        if not product:
            raise AppError("errors.not_found", 404, {"entity": "product"})
        _require_project_scope(_product_project_id(db, product), user_data)

        ledger_balance = int(
            db.scalar(
                select(func.coalesce(func.sum(InventoryLedger.quantity_delta), 0)).where(
                    InventoryLedger.id_product == product.id_product
                )
            )
            or 0
        )
        last = db.scalars(
            select(InventoryLedger)
            .where(InventoryLedger.id_product == product.id_product)
            .order_by(InventoryLedger.id_inventory_ledger.desc())
            .limit(1)
        ).first()
        stock_balance = int(product.cantidad or 0)
        return {
            "id_product": product.id_product,
            "stock_balance": stock_balance,
            "ledger_balance": ledger_balance,
            "difference": stock_balance - ledger_balance,
            "is_reconciled": stock_balance == ledger_balance,
            "last_movement_balance": last.balance_after if last else None,
            "movements": db.scalar(
                select(func.count()).select_from(
                    select(InventoryLedger.id_inventory_ledger)
                    .where(InventoryLedger.id_product == product.id_product)
                    .subquery()
                )
            )
            or 0,
        }
