"""Enlace entre facturar y descontar existencias.

El libro de inventario ya tenia el campo para decir de donde viene un
movimiento, pero nada lo llenaba desde una factura: se facturaba y el almacen
quedaba igual, de modo que la existencia y lo vendido se separaban solas.

Aqui se descargan las partidas de una factura de venta contra el almacen.
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

* **Solo facturas de venta.** Una factura de compra no descuenta; al
  contrario, es la que trae la mercancia.
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


REFERENCE_TYPE = "invoice_line"

# Estatus de factura desde los que tiene sentido descargar: ya es un
# comprobante, no una cotizacion.
DISCHARGEABLE_STATUSES = {"timbrada", "pendiente", "pagada", "parcial"}


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


def _line_plan(db, invoice, line, requested_locations):
    """Que haria la descarga con esta partida, y si puede hacerse."""
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
        "already_discharged": False,
        "dischargeable": False,
        "skip_reason": None,
    }

    existing = db.scalars(
        select(InventoryLedger).where(InventoryLedger.idempotency_key == _movement_key(invoice.id_invoice, line_id))
    ).first()
    if existing:
        plan.update({
            "already_discharged": True,
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

    if available < units:
        plan["skip_reason"] = "insufficient_stock"
        return plan

    plan["dischargeable"] = True
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


def preview_invoice_discharge(invoice_id, payload, user_data) -> dict:
    """Que se descargaria de esta factura, sin tocar el almacen."""
    with transaction_context() as db:
        invoice = _load_invoice(db, invoice_id, user_data)
        direction = _invoice_direction(db, invoice)
        status = str(invoice.invoice_status or "").strip().lower()
        locations = _requested_locations(payload)
        plans = [_line_plan(db, invoice, line, locations) for line in _authorized_lines(db, invoice.id_invoice)]

        blocking = [plan for plan in plans if plan["skip_reason"] == "insufficient_stock"]
        pending = [plan for plan in plans if plan["dischargeable"]]
        return {
            "id_invoice": invoice.id_invoice,
            "invoice_status": invoice.invoice_status,
            "invoice_direction": direction,
            "is_sale": direction == "venta",
            "status_allows_discharge": status in DISCHARGEABLE_STATUSES,
            "lines": plans,
            "pending_lines": len(pending),
            "already_discharged_lines": len([plan for plan in plans if plan["already_discharged"]]),
            "blocked_lines": len(blocking),
            "fully_discharged": bool(plans) and not pending and not blocking and any(
                plan["already_discharged"] for plan in plans
            ),
            "can_discharge": (
                direction == "venta"
                and status in DISCHARGEABLE_STATUSES
                and bool(pending)
                and not blocking
            ),
        }


def discharge_invoice_inventory(invoice_id, payload, user_data) -> dict:
    """Descuenta del almacen las partidas de una factura de venta.

    Todas las partidas en una sola transaccion. Repetir la llamada no vuelve a
    descontar: la llave del movimiento se deriva de la factura y la partida.
    """
    payload = payload or {}
    locations = _requested_locations(payload)

    with transaction_context() as db:
        invoice = _load_invoice(db, invoice_id, user_data)
        direction = _invoice_direction(db, invoice)
        if direction != "venta":
            raise AppError(
                "errors.invoice_discharge_requires_sale",
                409,
                {"invoice_direction": direction},
            )
        status = str(invoice.invoice_status or "").strip().lower()
        if status not in DISCHARGEABLE_STATUSES:
            raise AppError(
                "errors.invoice_discharge_status_not_allowed",
                409,
                {"invoice_status": invoice.invoice_status, "allowed": sorted(DISCHARGEABLE_STATUSES)},
            )

        lines = _authorized_lines(db, invoice.id_invoice)
        if not lines:
            raise AppError("errors.invoice_discharge_no_lines", 409, {"id_invoice": invoice.id_invoice})

        plans = [_line_plan(db, invoice, line, locations) for line in lines]
        blocked = [plan for plan in plans if plan["skip_reason"] == "insufficient_stock"]
        if blocked:
            # Se corta antes de escribir: descargar solo las partidas que
            # alcanzan dejaria la factura a medias contra el almacen.
            raise AppError(
                "errors.inventory_insufficient_stock",
                409,
                {"lines": blocked},
            )

        movements = []
        skipped = []
        for plan in plans:
            if plan["already_discharged"]:
                skipped.append({**plan, "skip_reason": "already_discharged"})
                continue
            if not plan["dischargeable"]:
                skipped.append(plan)
                continue
            movement, created = apply_movement_in_session(
                db,
                plan["id_product"],
                user_data,
                movement_type="issue",
                quantity_delta=-plan["units"],
                idempotency_key=_movement_key(invoice.id_invoice, plan["id_invoice_material_service"]),
                id_location=plan["id_location"],
                reference_type=REFERENCE_TYPE,
                reference_id=str(plan["id_invoice_material_service"]),
                reason=f"Salida por factura {invoice.id_invoice}",
            )
            movements.append({**movement, "id_invoice_material_service": plan["id_invoice_material_service"], "created": created})

        return {
            "id_invoice": invoice.id_invoice,
            "discharged_lines": len(movements),
            "skipped_lines": skipped,
            "movements": movements,
        }
