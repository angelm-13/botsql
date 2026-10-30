"""Enlace entre facturar y mover existencias.

El libro de inventario ya tenia el campo para decir de donde viene un
movimiento, pero nada lo llenaba desde una factura: se facturaba y el almacen
quedaba igual, de modo que la existencia y lo facturado se separaban solas.

Una factura mueve el almacen en la direccion que le corresponde:

* **Venta**: saca la mercancia. Lo que se factura al cliente deja de estar en
  el almacen.
* **Compra**: la mete. Una factura de proveedor es justamente el documento con
  el que la mercancia entra.

Es la misma operacion en los dos casos, y el sentido lo decide la direccion de
la factura, no quien la llama. Asi no hay forma de pedir la operacion
equivocada por descuido.

Decisiones que conviene tener presentes:

* **La descarga es un paso aparte del timbrado.** Timbrar consume un folio ante
  el SAT y no se puede deshacer; si la descarga fuera parte de la misma
  operacion, una falta de existencia dejaria el comprobante emitido y la
  transaccion revertida, o al contrario. Por eso el timbrado nunca falla por
  inventario: primero se emite el comprobante y despues se descarga.

* **Todo o nada.** Las partidas de una factura se aplican en una sola
  transaccion. Descargar la mitad dejaria el almacen en un estado que nadie
  puede explicar.

* **Idempotente por partida.** La llave del movimiento se deriva de la factura
  y la partida, asi que repetir la descarga no vuelve a descontar. Es lo que
  permite reintentar sin miedo cuando algo se corta a medias.

* **La direccion la manda la factura.** Una factura sin clasificar no mueve
  nada: sin saber si entra o sale, cualquier movimiento seria una adivinanza.

* **Una partida CAUSA un movimiento o lo DOCUMENTA, nunca las dos.** Una venta
  de mostrador ya descuenta del almacen al cobrarse. Si despues se factura y la
  factura tambien descuenta, el producto sale dos veces del inventario por
  haberse vendido una vez. El saldo queda mal y nada avisa, porque las dos
  operaciones son correctas por separado.

  `invoice.source_module` distingue los dos casos. Vacio: la factura es el
  origen del movimiento -una venta capturada aqui, una compra a proveedor- y por
  lo tanto mueve. Con valor: la venta ya ocurrio en el punto de venta o en el
  restaurante y ya movio; la factura solo la respalda ante el SAT.

  Lo que se devuelve en ese caso no es "no hice nada", sino los movimientos que
  la venta ya escribio. La factura tiene que poder decir de donde salio su
  mercancia, aunque no la haya movido ella.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from sqlalchemy import select

from app.models.customer_supplier import CustomerSupplier
from app.models.inventory_ledger import InventoryLedger
from app.models.inventory_stock import InventoryStock
from app.models.invoice import Invoice
from app.models.invoice_material_service import InvoiceMaterialService
from app.models.location import Location
from app.models.product import Product
from app.models.session import transaction_context
from app.services.inventory_service import apply_movement_in_session
from app.services.invoice_xml_classification import classify_invoice_direction, normalize_rfc
from app.utils.errors import AppError
from app.utils.tiempo import a_iso_utc


REFERENCE_TYPE = "invoice_line"

# Estatus de factura desde los que tiene sentido mover el almacen: ya es un
# comprobante, no una cotizacion.
APPLICABLE_STATUSES = {"timbrada", "pendiente", "pagada", "parcial"}

# Que movimiento genera cada direccion. Una venta saca del almacen; una compra
# lo surte.
DIRECTION_MOVEMENTS = {
    "venta": ("issue", -1),
    "compra": ("receive", 1),
}


def _movement_key(invoice_id, line_id) -> str:
    """Deriva la llave del movimiento para que repetir no vuelva a descontar."""
    return f"invoice-{int(invoice_id)}-line-{int(line_id)}"


def _principal_rfc(db) -> str:
    company = db.scalars(
        select(CustomerSupplier)
        .where(CustomerSupplier.is_principal.is_(True))
        .where(CustomerSupplier.deletion_date.is_(None))
    ).first()
    return normalize_rfc(getattr(company, "tax_id", None))


def _invoice_direction(db, invoice) -> str:
    """Venta o compra.

    Se respeta lo que la factura declare; si no lo declara, se deduce
    comparando su emisor y receptor con la empresa principal, con la misma
    regla que usa la carga de XML. Las facturas capturadas a mano no traen
    direccion, y sin esta deduccion no se podrian descargar.
    """
    declared = str(getattr(invoice, "invoice_direction", "") or "").strip().lower()
    if declared in {"venta", "compra"}:
        return declared

    issuer = db.get(CustomerSupplier, invoice.id_issuer_customer_supplier)
    receiver = db.get(CustomerSupplier, invoice.id_customer_supplier)
    return classify_invoice_direction(
        _principal_rfc(db),
        getattr(issuer, "tax_id", None) or invoice.nombre_emisor,
        getattr(receiver, "tax_id", None) or invoice.rfc_receptor,
    )


def _authorize(invoice, user_data):
    if not invoice.id_proyect:
        raise AppError("errors.resource_scope_missing", 409)
    unrestricted = bool(user_data.get("is_superuser") or user_data.get("is_bootstrap_admin"))
    actor_project = user_data.get("id_proyect") or user_data.get("project_id")
    if not unrestricted and str(actor_project) != str(invoice.id_proyect):
        raise AppError("errors.permission_denied", 403)


def _load_invoice(db, invoice_id, user_data):
    invoice = db.get(Invoice, int(invoice_id))
    if not invoice or invoice.deletion_date is not None:
        raise AppError("errors.resource_not_found", 404)
    _authorize(invoice, user_data)
    return invoice


def _authorized_lines(db, invoice_id):
    return db.scalars(
        select(InvoiceMaterialService)
        .where(InvoiceMaterialService.id_invoice == int(invoice_id))
        .where(InvoiceMaterialService.authorization_status == "authorized")
        .where(InvoiceMaterialService.deletion_date.is_(None))
        .order_by(InvoiceMaterialService.id_invoice_material_service)
    ).all()


def _whole_units(value):
    """La existencia se lleva en piezas enteras.

    Las partidas admiten seis decimales, asi que una venta de 2.5 kilos no se
    puede descontar de un inventario que cuenta piezas. Se devuelve None para
    que el llamador lo reporte en lugar de redondear a la callada, que
    descuadraria el almacen sin dejar rastro.
    """
    try:
        quantity = Decimal(str(value if value is not None else 0))
    except (InvalidOperation, TypeError, ValueError):
        return None
    if quantity <= 0 or quantity != quantity.to_integral_value():
        return None
    return int(quantity)


def _available_units(db, product, location) -> int:
    """Existencia del producto en esa ubicacion.

    Un producto que nunca se ha movido todavia no tiene fila de existencia; su
    `cantidad` esta en la ubicacion propia y se contara ahi cuando el
    movimiento la siembre. Fuera de esa ubicacion, no hay nada.
    """
    stock = db.scalars(
        select(InventoryStock)
        .where(InventoryStock.id_product == product.id_product)
        .where(InventoryStock.id_location == location.id_location)
    ).first()
    if stock is not None:
        return int(stock.quantity or 0)

    seeded = db.scalars(
        select(InventoryStock).where(InventoryStock.id_product == product.id_product)
    ).first()
    if seeded is None and product.id_location == location.id_location:
        return int(product.cantidad or 0)
    return 0


def _line_plan(db, invoice, line, requested_locations, direction):
    """Que haria la factura con esta partida, y si puede hacerse.

    En una venta hay que comprobar que haya existencia; en una compra no,
    porque la mercancia esta entrando.
    """
    line_id = line.id_invoice_material_service
    plan = {
        "id_invoice_material_service": line_id,
        "description": line.invoice_material_service_description,
        "quantity": str(line.quantity or 0),
        "id_product": line.id_product,
        "units": None,
        "id_location": None,
        "location_description": None,
        "available": None,
        "already_applied": False,
        "applicable": False,
        "skip_reason": None,
    }

    existing = db.scalars(
        select(InventoryLedger).where(InventoryLedger.idempotency_key == _movement_key(invoice.id_invoice, line_id))
    ).first()
    if existing:
        plan.update({
            "already_applied": True,
            "units": abs(int(existing.quantity_delta)),
            "id_location": existing.id_location,
        })
        return plan

    if not line.id_product:
        # Servicios y materiales sin producto no viven en el almacen.
        plan["skip_reason"] = "line_without_product"
        return plan

    product = db.get(Product, line.id_product)
    if not product or product.deletion_date is not None:
        plan["skip_reason"] = "product_not_found"
        return plan

    # Un activo de uso interno -herramienta, equipo- no se vende. Sale para
    # usarse, prestarse o consumirse, y para eso esta el rastreo de piezas. Si
    # se dejara pasar, una venta descontaria del almacen de la empresa una
    # herramienta que sigue siendo suya, y el saldo quedaria diciendo que ya no
    # la tiene.
    #
    # Se reporta como partida no aplicable en lugar de reventar la factura
    # entera: la venta puede ser legitima -se vendio una herramienta vieja- y en
    # ese caso el producto se reclasifica, que es una decision de quien opera y
    # no algo que el sistema deba adivinar.
    proposito = str(getattr(product, "stock_purpose", "mercancia") or "mercancia")
    if direction == "venta" and proposito == "uso_interno":
        plan["skip_reason"] = "product_is_for_internal_use"
        plan["stock_purpose"] = proposito
        return plan

    units = _whole_units(line.quantity)
    if units is None:
        plan["skip_reason"] = "quantity_not_whole_units"
        return plan
    plan["units"] = units

    location_id = requested_locations.get(line_id) or requested_locations.get("default") or product.id_location
    location = db.get(Location, int(location_id)) if location_id else None
    if not location or location.deletion_date is not None:
        plan["skip_reason"] = "location_not_found"
        return plan
    plan["id_location"] = location.id_location
    plan["location_description"] = location.location_description

    available = _available_units(db, product, location)
    plan["available"] = available

    # Solo la salida depende de que haya existencia. Una compra surte.
    if direction == "venta" and available < units:
        plan["skip_reason"] = "insufficient_stock"
        return plan

    plan["applicable"] = True
    return plan


def _requested_locations(payload) -> dict:
    """Ubicacion de salida: una para toda la factura o una por partida."""
    payload = payload or {}
    locations = {}
    if payload.get("id_location"):
        locations["default"] = payload["id_location"]
    for key, value in (payload.get("locations_by_line") or {}).items():
        try:
            locations[int(key)] = value
        except (TypeError, ValueError) as exc:
            raise AppError("errors.invalid_field", 400, {"field": "locations_by_line"}) from exc
    return locations


def documenta_una_venta(invoice) -> bool:
    """Si esta factura respalda una venta que ya movio el almacen."""
    return bool(getattr(invoice, "source_module", None))


def _movimientos_de_la_venta(db, invoice) -> list[dict]:
    """Los renglones del libro que escribio la venta que esta factura documenta.

    Se buscan por el par (tipo de referencia, referencia) que dejo el modulo de
    origen al cobrar, no por la factura: la factura no los causo.
    """
    filas = db.scalars(
        select(InventoryLedger).where(
            InventoryLedger.reference_type == "sale",
            InventoryLedger.reference_id == str(invoice.source_reference or ""),
            InventoryLedger.source_module == invoice.source_module,
        ).order_by(InventoryLedger.id_inventory_ledger)
    ).all()
    return [
        {
            "id_inventory_ledger": fila.id_inventory_ledger,
            "id_product": fila.id_product,
            "id_location": fila.id_location,
            "movement_type": fila.movement_type,
            "quantity_delta": int(fila.quantity_delta or 0),
            "creation_date": a_iso_utc(fila.creation_date),
        }
        for fila in filas
    ]


def _respaldo_de_venta(db, invoice) -> dict:
    """Lo que hay que responder cuando la factura documenta en vez de mover.

    Se informa aunque no haya movimientos: una factura que dice venir de una
    venta y no encuentra su rastro en el libro es un descuadre que alguien tiene
    que mirar, no un caso normal que se pueda callar.
    """
    movimientos = _movimientos_de_la_venta(db, invoice)
    return {
        "id_invoice": invoice.id_invoice,
        "invoice_status": invoice.invoice_status,
        "documents_sale": True,
        "source_module": invoice.source_module,
        "source_reference": invoice.source_reference,
        "movement_type": None,
        "effect": "ninguno",
        "reason": "sale_already_moved_inventory",
        "sale_movements": movimientos,
        "sale_movement_count": len(movimientos),
        # Una factura de una venta cuyo movimiento no aparece: o la venta no
        # descuento -producto sin enlace al almacen- o alguien borro el renglon.
        "sale_movements_missing": not movimientos,
        "lines": [],
        "pending_lines": 0,
        "already_applied_lines": 0,
        "blocked_lines": 0,
        "fully_applied": True,
        "status_allows_apply": False,
        "can_apply": False,
    }


def preview_invoice_inventory(invoice_id, payload, user_data) -> dict:
    """Que movería esta factura en el almacen, sin tocar nada."""
    with transaction_context() as db:
        invoice = _load_invoice(db, invoice_id, user_data)
        if documenta_una_venta(invoice):
            return _respaldo_de_venta(db, invoice)
        direction = _invoice_direction(db, invoice)
        status = str(invoice.invoice_status or "").strip().lower()
        locations = _requested_locations(payload)
        plans = [
            _line_plan(db, invoice, line, locations, direction)
            for line in _authorized_lines(db, invoice.id_invoice)
        ]

        movement_type = DIRECTION_MOVEMENTS.get(direction, (None, 0))[0]
        blocking = [plan for plan in plans if plan["skip_reason"] == "insufficient_stock"]
        pending = [plan for plan in plans if plan["applicable"]]
        return {
            "id_invoice": invoice.id_invoice,
            "invoice_status": invoice.invoice_status,
            "invoice_direction": direction,
            "movement_type": movement_type,
            "effect": {"venta": "decrementa", "compra": "incrementa"}.get(direction, "ninguno"),
            "status_allows_apply": status in APPLICABLE_STATUSES,
            "lines": plans,
            "pending_lines": len(pending),
            "already_applied_lines": len([plan for plan in plans if plan["already_applied"]]),
            "blocked_lines": len(blocking),
            "fully_applied": bool(plans) and not pending and not blocking and any(
                plan["already_applied"] for plan in plans
            ),
            "can_apply": (
                direction in DIRECTION_MOVEMENTS
                and status in APPLICABLE_STATUSES
                and bool(pending)
                and not blocking
            ),
        }


def apply_invoice_to_inventory(invoice_id, payload, user_data) -> dict:
    """Mueve el almacen segun la factura: una venta saca, una compra mete.

    Todas las partidas en una sola transaccion. Repetir la llamada no vuelve a
    mover: la llave del movimiento se deriva de la factura y la partida.
    """
    payload = payload or {}
    locations = _requested_locations(payload)

    with transaction_context() as db:
        invoice = _load_invoice(db, invoice_id, user_data)
        # La venta ya movio el almacen al cobrarse. Aplicar aqui sacaria el
        # producto dos veces por haberse vendido una.
        if documenta_una_venta(invoice):
            respaldo = _respaldo_de_venta(db, invoice)
            respaldo["applied"] = []
            respaldo["applied_lines"] = 0
            return respaldo
        direction = _invoice_direction(db, invoice)
        if direction not in DIRECTION_MOVEMENTS:
            # Sin saber si entra o sale, cualquier movimiento seria una
            # adivinanza sobre el inventario de alguien.
            raise AppError(
                "errors.invoice_inventory_direction_unknown",
                409,
                {"invoice_direction": direction, "allowed": sorted(DIRECTION_MOVEMENTS)},
            )
        movement_type, sign = DIRECTION_MOVEMENTS[direction]

        status = str(invoice.invoice_status or "").strip().lower()
        if status not in APPLICABLE_STATUSES:
            raise AppError(
                "errors.invoice_inventory_status_not_allowed",
                409,
                {"invoice_status": invoice.invoice_status, "allowed": sorted(APPLICABLE_STATUSES)},
            )

        lines = _authorized_lines(db, invoice.id_invoice)
        if not lines:
            raise AppError("errors.invoice_inventory_no_lines", 409, {"id_invoice": invoice.id_invoice})

        plans = [_line_plan(db, invoice, line, locations, direction) for line in lines]
        blocked = [plan for plan in plans if plan["skip_reason"] == "insufficient_stock"]
        if blocked:
            # Se corta antes de escribir: aplicar solo las partidas que
            # alcanzan dejaria la factura a medias contra el almacen.
            raise AppError("errors.inventory_insufficient_stock", 409, {"lines": blocked})

        reason = {
            "venta": f"Salida por factura de venta {invoice.id_invoice}",
            "compra": f"Entrada por factura de compra {invoice.id_invoice}",
        }[direction]

        movements = []
        skipped = []
        for plan in plans:
            if plan["already_applied"]:
                skipped.append({**plan, "skip_reason": "already_applied"})
                continue
            if not plan["applicable"]:
                skipped.append(plan)
                continue
            movement, created = apply_movement_in_session(
                db,
                plan["id_product"],
                user_data,
                movement_type=movement_type,
                quantity_delta=sign * plan["units"],
                idempotency_key=_movement_key(invoice.id_invoice, plan["id_invoice_material_service"]),
                id_location=plan["id_location"],
                reference_type=REFERENCE_TYPE,
                reference_id=str(plan["id_invoice_material_service"]),
                reason=reason,
            )
            movements.append({
                **movement,
                "id_invoice_material_service": plan["id_invoice_material_service"],
                "created": created,
            })

        return {
            "id_invoice": invoice.id_invoice,
            "invoice_direction": direction,
            "movement_type": movement_type,
            "applied_lines": len(movements),
            "skipped_lines": skipped,
            "movements": movements,
        }
