"""Movimientos de inventario con existencia por ubicacion y almacen.

Modelo: el almacen no es una tabla propia, es una ubicacion cuyo tipo esta
marcado como almacen (`location_type.is_warehouse`). Las ubicaciones cuelgan
unas de otras, asi que un almacen contiene zonas, racks y posiciones, y la
existencia se guarda en la ubicacion concreta donde esta la mercancia.

Tres invariantes que este modulo sostiene y que las pruebas fijan:

* `inventory_stock` nunca queda negativa: una salida que no alcanza se
  rechaza antes de escribir.
* `product.cantidad` es siempre la suma de las existencias por ubicacion de
  ese producto. Se conserva porque el resto del sistema la lee.
* El libro es de solo agregado, y la suma de sus deltas por ubicacion cuadra
  con la existencia de esa ubicacion.

Un traspaso escribe dos renglones en el libro (la salida y la entrada) unidos
por `transfer_group`, dentro de la misma transaccion: o se mueven las dos
puntas o no se mueve ninguna.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select

from app.models.entity_permission import EntityPermission
from app.models.inventory_ledger import InventoryLedger
from app.models.inventory_stock import InventoryStock
from app.models.invoice import Invoice
from app.models.location import Location
from app.models.location_type import LocationType
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

# Movimientos que exigen un motivo escrito: cambian la existencia sin un
# documento detras, asi que sin motivo el inventario deja de ser auditable.
REASON_REQUIRED_MOVEMENTS = {"adjustment", "damage", "destroy", "loss", "transfer"}

REFERENCE_TYPES = {
    "invoice", "invoice_line", "purchase", "project", "task", "incident",
    "count", "manual", "transfer",
}

# Profundidad maxima al subir por el arbol de ubicaciones buscando el almacen.
# Es una red contra datos ciclicos, no un limite de dise~no.
MAX_LOCATION_DEPTH = 20

# El ajuste es el unico movimiento sin documento detras y sin tope: puede
# crear o destruir existencia por cualquier cantidad. Es justo la operacion con
# la que se tapa un faltante, asi que exige una capacidad aparte en lugar de
# bastar con el permiso de editar productos. Los demas movimientos estan
# acotados por un documento o por la existencia disponible.
ADJUSTMENT_CAPABILITY = "inventory_adjustment"
READ_BIT = 2


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


def _is_unrestricted(user_data) -> bool:
    return bool(user_data.get("is_superuser") or user_data.get("is_bootstrap_admin"))


def has_capability(db, user_data, capability) -> bool:
    """Capacidad concedida al rol del actor, con el mismo mecanismo que Proyectos."""
    if _is_unrestricted(user_data):
        return True
    try:
        permission_id = int(user_data.get("id_permission") or user_data.get("permission_id") or 0)
    except (TypeError, ValueError):
        return False
    if not permission_id:
        return False
    record = (
        db.query(EntityPermission)
        .filter(EntityPermission.id_permission == permission_id)
        .filter(EntityPermission.entity_name == capability)
        .filter(EntityPermission.deletion_date.is_(None))
        .first()
    )
    try:
        return bool(record and int(record.control_type) & READ_BIT)
    except (TypeError, ValueError):
        return False


def _require_adjustment_capability(db, user_data):
    if not has_capability(db, user_data, ADJUSTMENT_CAPABILITY):
        raise AppError(
            "errors.inventory_adjustment_not_authorized",
            403,
            {"capability": ADJUSTMENT_CAPABILITY},
        )


def _actor_project_id(user_data):
    value = user_data.get("id_proyect") or user_data.get("project_id")
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _required_reason(payload, movement_type):
    reason = str(payload.get("reason") or "").strip()
    if movement_type in REASON_REQUIRED_MOVEMENTS and not reason:
        raise AppError(
            "errors.inventory_reason_required",
            400,
            {"field": "reason", "movement_type": movement_type},
        )
    return reason[:250] or None


def _reference_type(payload):
    value = str(payload.get("reference_type") or "").strip().lower()
    if not value:
        return None
    if value not in REFERENCE_TYPES:
        raise AppError(
            "errors.invalid_field",
            400,
            {"field": "reference_type", "allowed": sorted(REFERENCE_TYPES)},
        )
    return value


def _idempotency_key(payload):
    key = str(payload.get("idempotency_key") or "").strip()
    if not key or len(key) > 90:
        raise AppError("errors.invalid_field", 400, {"field": "idempotency_key"})
    return key


def _location(db, location_id, field="id_location"):
    try:
        location_id = int(location_id)
    except (TypeError, ValueError) as exc:
        raise AppError("errors.invalid_field", 400, {"field": field}) from exc
    location = db.get(Location, location_id)
    if not location or location.deletion_date is not None:
        raise AppError("errors.not_found", 404, {"entity": "location", "field": field})
    return location


def resolve_warehouse(db, location) -> Location | None:
    """Sube por el arbol hasta la ubicacion marcada como almacen.

    Devuelve None si ninguna ubicacion de la rama es almacen, que es el caso
    de los datos que existian antes de esta funcionalidad.
    """
    current = location
    seen = set()
    for _ in range(MAX_LOCATION_DEPTH):
        if current is None or current.id_location in seen:
            return None
        seen.add(current.id_location)
        location_type = db.get(LocationType, current.id_location_type)
        if location_type is not None and bool(location_type.is_warehouse):
            return current
        if current.id_location_reference is None:
            return None
        current = db.get(Location, current.id_location_reference)
    return None


def _warehouse_payload(db, location) -> dict:
    warehouse = resolve_warehouse(db, location)
    return {
        "id_location": location.id_location,
        "location_description": location.location_description,
        "id_warehouse": warehouse.id_location if warehouse else None,
        "warehouse_description": warehouse.location_description if warehouse else None,
    }


def _stock_row(db, product_id, location_id, actor_id, *, for_update=False):
    query = select(InventoryStock).where(
        InventoryStock.id_product == product_id,
        InventoryStock.id_location == location_id,
    )
    if for_update:
        query = query.with_for_update()
    row = db.scalars(query).first()
    if row is None:
        row = InventoryStock(
            id_product=product_id,
            id_location=location_id,
            quantity=0,
            created_by=actor_id,
        )
        db.add(row)
        db.flush()
    return row


def _ensure_stock_seeded(db, product) -> None:
    """Traslada `product.cantidad` a la existencia por ubicacion la primera vez.

    La migracion sembro los productos que existian, pero un producto creado
    despues por la via normal de altas trae `cantidad` sin ninguna fila de
    existencia. Sin esto su saldo arrancaria en cero y el primer movimiento
    perderia lo que ya habia.
    """
    already = db.scalar(
        select(func.count()).select_from(InventoryStock)
        .where(InventoryStock.id_product == product.id_product)
    )
    if already:
        return
    quantity = int(product.cantidad or 0)
    if quantity <= 0 or not product.id_location:
        return
    db.add(InventoryStock(
        id_product=product.id_product,
        id_location=product.id_location,
        quantity=quantity,
        created_by=int(product.created_by or 1),
    ))
    db.flush()


def _product_total(db, product_id) -> int:
    total = db.scalar(
        select(func.coalesce(func.sum(InventoryStock.quantity), 0))
        .where(InventoryStock.id_product == product_id)
    )
    return int(total or 0)


def _authorize(db, product, user_data):
    """El producto pertenece a un proyecto via su factura de compra."""
    invoice = db.get(Invoice, product.id_invoice)
    project_id = getattr(invoice, "id_proyect", None)
    if not project_id:
        raise AppError("errors.resource_scope_missing", 409)
    unrestricted = bool(user_data.get("is_superuser") or user_data.get("is_bootstrap_admin"))
    if not unrestricted and _actor_project_id(user_data) != project_id:
        raise AppError("errors.permission_denied", 403)
    return project_id


def _locked_product(db, product_id):
    product = db.scalars(
        select(Product).where(Product.id_product == product_id).with_for_update()
    ).first()
    if not product:
        raise AppError("errors.not_found", 404, {"entity": "product"})
    return product


def _append_ledger(db, **values):
    ledger = InventoryLedger(**values)
    db.add(ledger)
    db.flush()
    return ledger


def apply_inventory_movement(product_id, payload, user_data):
    """Entrada, salida o ajuste de un producto en una ubicacion.

    Si no se indica ubicacion se usa la del producto, para que las llamadas
    escritas antes de los almacenes sigan funcionando igual.
    """
    movement_type = str(payload.get("movement_type") or "").strip().lower()
    if movement_type == "transfer":
        raise AppError(
            "errors.inventory_transfer_requires_endpoint",
            400,
            {"field": "movement_type", "use": "POST /product/<id>/inventory-transfers"},
        )
    if movement_type not in {*MOVEMENT_SIGNS, "adjustment"}:
        raise AppError(
            "errors.invalid_field",
            400,
            {"field": "movement_type", "allowed": sorted({*MOVEMENT_SIGNS, "adjustment"})},
        )

    key = _idempotency_key(payload)
    reason = _required_reason(payload, movement_type)
    reference_type = _reference_type(payload)

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
        return apply_movement_in_session(
            db,
            product_id,
            user_data,
            movement_type=movement_type,
            quantity_delta=quantity_delta,
            idempotency_key=key,
            id_location=payload.get("id_location"),
            reference_type=reference_type,
            reference_id=payload.get("reference_id"),
            reason=reason,
        )


def apply_movement_in_session(
    db,
    product_id,
    user_data,
    *,
    movement_type,
    quantity_delta,
    idempotency_key,
    id_location=None,
    reference_type=None,
    reference_id=None,
    reason=None,
):
    """Nucleo de un movimiento, dentro de una transaccion que abre el llamador.

    Existe aparte para que varias partidas de una factura se descarguen en una
    sola transaccion: si una falla, ninguna se aplica. Los validadores de la
    entrada publica ya corrieron cuando se llega aqui.
    """
    # La capacidad de ajustar se comprueba aqui y no solo en la entrada
    # publica: cualquier camino que llegue a este nucleo queda cubierto.
    if movement_type == "adjustment":
        _require_adjustment_capability(db, user_data)

    previous = db.scalars(
        select(InventoryLedger).where(InventoryLedger.idempotency_key == idempotency_key)
    ).first()
    if previous:
        if previous.id_product != int(product_id):
            raise AppError("errors.idempotency_conflict", 409)
        return previous.serialize(), False

    product = _locked_product(db, product_id)
    project_id = _authorize(db, product, user_data)
    _ensure_stock_seeded(db, product)
    location = _location(db, id_location or product.id_location)

    actor_id = int(user_data.get("id_user") or 0)
    stock = _stock_row(db, product.id_product, location.id_location, actor_id, for_update=True)
    location_balance = int(stock.quantity or 0) + quantity_delta
    if location_balance < 0:
        raise AppError(
            "errors.inventory_insufficient_stock",
            409,
            {
                "available": int(stock.quantity or 0),
                "requested": abs(quantity_delta),
                "id_product": product.id_product,
                "id_location": location.id_location,
                "location_description": location.location_description,
            },
        )

    stock.quantity = location_balance
    db.flush()
    product.cantidad = _product_total(db, product.id_product)

    ledger = _append_ledger(
        db,
        id_product=product.id_product,
        id_proyect=project_id,
        movement_type=movement_type,
        quantity_delta=quantity_delta,
        balance_after=product.cantidad,
        id_location=location.id_location,
        location_balance_after=location_balance,
        idempotency_key=idempotency_key,
        reference_type=reference_type,
        reference_id=str(reference_id or "").strip()[:100] or None,
        reason=reason,
        created_by=actor_id,
    )
    return ledger.serialize(), True


def transfer_inventory(product_id, payload, user_data):
    """Mueve existencia de una ubicacion a otra en una sola transaccion.

    Escribe dos renglones en el libro unidos por `transfer_group`: la salida
    del origen y la entrada al destino. Si algo falla, no se mueve ninguna de
    las dos puntas.
    """
    key = _idempotency_key(payload)
    quantity = _integer_quantity(payload.get("quantity"))
    reason = _required_reason(payload, "transfer")

    with transaction_context() as db:
        outbound_key = f"{key}:out"
        previous = db.scalars(
            select(InventoryLedger).where(InventoryLedger.idempotency_key == outbound_key)
        ).first()
        if previous:
            if previous.id_product != int(product_id):
                raise AppError("errors.idempotency_conflict", 409)
            pair = db.scalars(
                select(InventoryLedger)
                .where(InventoryLedger.transfer_group == previous.transfer_group)
                .order_by(InventoryLedger.id_inventory_ledger)
            ).all()
            return {"movements": [row.serialize() for row in pair]}, False

        product = _locked_product(db, product_id)
        project_id = _authorize(db, product, user_data)
        _ensure_stock_seeded(db, product)
        origin = _location(db, payload.get("id_location_from"), "id_location_from")
        target = _location(db, payload.get("id_location_to"), "id_location_to")
        if origin.id_location == target.id_location:
            raise AppError(
                "errors.inventory_transfer_same_location",
                400,
                {"field": "id_location_to"},
            )

        actor_id = int(user_data.get("id_user") or 0)
        # Se bloquean las dos filas en orden de identificador: si dos traspasos
        # cruzados corren a la vez, tomar los candados siempre en el mismo
        # orden evita que se queden esperando uno al otro.
        first, second = sorted([origin.id_location, target.id_location])
        rows = {
            location_id: _stock_row(db, product.id_product, location_id, actor_id, for_update=True)
            for location_id in (first, second)
        }
        origin_stock = rows[origin.id_location]
        target_stock = rows[target.id_location]

        available = int(origin_stock.quantity or 0)
        if available < quantity:
            raise AppError(
                "errors.inventory_insufficient_stock",
                409,
                {
                    "available": available,
                    "requested": quantity,
                    "id_location": origin.id_location,
                    "location_description": origin.location_description,
                },
            )

        origin_stock.quantity = available - quantity
        target_stock.quantity = int(target_stock.quantity or 0) + quantity
        db.flush()
        # El total del producto no cambia en un traspaso, pero se recalcula
        # para no dar por hecho el estado previo.
        product.cantidad = _product_total(db, product.id_product)

        group = str(uuid.uuid4())
        reference_id = str(payload.get("reference_id") or "").strip()[:100] or None
        common = {
            "id_product": product.id_product,
            "id_proyect": project_id,
            "movement_type": "transfer",
            "balance_after": product.cantidad,
            "reference_type": _reference_type(payload) or "transfer",
            "reference_id": reference_id,
            "reason": reason,
            "created_by": actor_id,
            "transfer_group": group,
        }
        outbound = _append_ledger(
            db,
            **common,
            quantity_delta=-quantity,
            id_location=origin.id_location,
            id_location_target=target.id_location,
            location_balance_after=origin_stock.quantity,
            idempotency_key=outbound_key,
        )
        inbound = _append_ledger(
            db,
            **common,
            quantity_delta=quantity,
            id_location=target.id_location,
            id_location_target=origin.id_location,
            location_balance_after=target_stock.quantity,
            idempotency_key=f"{key}:in",
        )
        return {"movements": [outbound.serialize(), inbound.serialize()]}, True


def product_stock(product_id, user_data) -> dict:
    """Donde esta repartido un producto, con su almacen y su total."""
    with transaction_context() as db:
        product = db.get(Product, int(product_id))
        if not product:
            raise AppError("errors.not_found", 404, {"entity": "product"})
        _authorize(db, product, user_data)
        _ensure_stock_seeded(db, product)

        rows = db.scalars(
            select(InventoryStock)
            .where(InventoryStock.id_product == product.id_product)
            .order_by(InventoryStock.id_location)
        ).all()
        items = []
        for row in rows:
            location = db.get(Location, row.id_location)
            items.append({
                **_warehouse_payload(db, location),
                "quantity": int(row.quantity or 0),
            })
        return {
            "id_product": product.id_product,
            "items": items,
            "total": sum(item["quantity"] for item in items),
            "stock_balance": int(product.cantidad or 0),
        }


def warehouse_stock(location_id, user_data) -> dict:
    """Que hay dentro de un almacen, sumando todas sus ubicaciones."""
    with transaction_context() as db:
        root = _location(db, location_id)
        descendants = _descendant_ids(db, root.id_location)

        rows = db.scalars(
            select(InventoryStock)
            .where(InventoryStock.id_location.in_(descendants))
            .where(InventoryStock.quantity > 0)
            .order_by(InventoryStock.id_product, InventoryStock.id_location)
        ).all()

        unrestricted = bool(user_data.get("is_superuser") or user_data.get("is_bootstrap_admin"))
        actor_project = _actor_project_id(user_data)
        items = []
        for row in rows:
            product = db.get(Product, row.id_product)
            invoice = db.get(Invoice, product.id_invoice) if product else None
            project_id = getattr(invoice, "id_proyect", None)
            # El almacen puede guardar mercancia de varios proyectos; se
            # muestra solo la que el actor tiene permitido ver.
            if not unrestricted and project_id != actor_project:
                continue
            location = db.get(Location, row.id_location)
            items.append({
                "id_product": row.id_product,
                "product_description": getattr(product, "descripcion", None),
                "product_code": getattr(product, "product_code", None),
                **_warehouse_payload(db, location),
                "quantity": int(row.quantity or 0),
            })
        return {
            "id_location": root.id_location,
            "location_description": root.location_description,
            "is_warehouse": bool(resolve_warehouse(db, root) is root),
            "locations_included": len(descendants),
            "items": items,
            "total": sum(item["quantity"] for item in items),
        }


def _descendant_ids(db, location_id) -> list[int]:
    """Identificadores de la ubicacion y todo lo que cuelga de ella."""
    collected = [int(location_id)]
    frontier = [int(location_id)]
    for _ in range(MAX_LOCATION_DEPTH):
        if not frontier:
            break
        children = db.scalars(
            select(Location.id_location)
            .where(Location.id_location_reference.in_(frontier))
            .where(Location.deletion_date.is_(None))
        ).all()
        # Un dato ciclico haria que esto no terminara; se corta por identidad.
        frontier = [child for child in children if child not in collected]
        collected.extend(frontier)
    return collected


def list_inventory_movements(product_id, user_data, *, page=1, per_page=50, movement_type=None, location_id=None) -> dict:
    """Libro de movimientos de un producto, filtrable por tipo y ubicacion."""
    try:
        page = max(int(page or 1), 1)
        per_page = min(max(int(per_page or 50), 1), 200)
    except (TypeError, ValueError):
        page, per_page = 1, 50

    with transaction_context() as db:
        product = db.get(Product, int(product_id))
        if not product:
            raise AppError("errors.not_found", 404, {"entity": "product"})
        _authorize(db, product, user_data)

        query = select(InventoryLedger).where(InventoryLedger.id_product == product.id_product)
        if movement_type:
            query = query.where(InventoryLedger.movement_type == str(movement_type).strip().lower())
        if location_id:
            query = query.where(InventoryLedger.id_location == int(location_id))

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
            "total": int(total),
            "balance": int(product.cantidad or 0),
        }


def reconcile_product_stock(product_id, user_data) -> dict:
    """Compara libro, existencia por ubicacion y total del producto.

    Son tres registros que deben coincidir. Si alguno se movio por fuera del
    flujo, aqui se ve; sin esta consulta un descuadre pasaba inadvertido.
    """
    with transaction_context() as db:
        product = db.get(Product, int(product_id))
        if not product:
            raise AppError("errors.not_found", 404, {"entity": "product"})
        _authorize(db, product, user_data)
        _ensure_stock_seeded(db, product)

        ledger_total = int(db.scalar(
            select(func.coalesce(func.sum(InventoryLedger.quantity_delta), 0))
            .where(InventoryLedger.id_product == product.id_product)
        ) or 0)
        stock_total = _product_total(db, product.id_product)
        product_balance = int(product.cantidad or 0)

        per_location = []
        rows = db.scalars(
            select(InventoryStock)
            .where(InventoryStock.id_product == product.id_product)
            .order_by(InventoryStock.id_location)
        ).all()
        for row in rows:
            ledger_at_location = int(db.scalar(
                select(func.coalesce(func.sum(InventoryLedger.quantity_delta), 0))
                .where(InventoryLedger.id_product == product.id_product)
                .where(InventoryLedger.id_location == row.id_location)
            ) or 0)
            per_location.append({
                "id_location": row.id_location,
                "stock_quantity": int(row.quantity or 0),
                "ledger_balance": ledger_at_location,
                "difference": int(row.quantity or 0) - ledger_at_location,
                "is_reconciled": int(row.quantity or 0) == ledger_at_location,
            })

        # El saldo que declaro el ultimo renglon del libro: si difiere del
        # total del producto, alguien lo movio por fuera del flujo.
        last_movement_balance = db.scalar(
            select(InventoryLedger.balance_after)
            .where(InventoryLedger.id_product == product.id_product)
            .order_by(InventoryLedger.id_inventory_ledger.desc())
            .limit(1)
        )

        return {
            "id_product": product.id_product,
            "ledger_balance": ledger_total,
            "stock_balance": stock_total,
            "product_balance": product_balance,
            "last_movement_balance": int(last_movement_balance) if last_movement_balance is not None else None,
            "difference": product_balance - ledger_total,
            "is_reconciled": product_balance == ledger_total == stock_total,
            "movements": int(db.scalar(
                select(func.count()).select_from(InventoryLedger)
                .where(InventoryLedger.id_product == product.id_product)
            ) or 0),
            "by_location": per_location,
        }
