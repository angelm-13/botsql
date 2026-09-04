"""Cancelacion de CFDI ante el SAT.

Cancelar no es borrar ni un interruptor. Se solicita al SAT indicando un
motivo, y de ahi puede salir cancelado de inmediato o quedar "en proceso"
esperando que el receptor acepte, con hasta 72 horas para responder. De esa
espera puede salir cancelado o rechazado. Por eso se guarda cada solicitud con
su desenlace, y no solo una bandera en la factura.

Reglas que aqui se aplican:

* Solo se cancela un comprobante timbrado. Una cotizacion o una factura sin
  folio fiscal no existe ante el SAT.
* El motivo 01 exige el folio fiscal del comprobante que sustituye a este, y
  ese comprobante tiene que existir y estar timbrado. Es el unico motivo que
  lleva sustitucion; los demas la prohiben.
* Una factura ya cancelada no se vuelve a cancelar, pero una solicitud
  rechazada si se puede volver a intentar con otro motivo.
* Cancelar una venta devuelve al almacen lo que esa factura habia descontado.
  Se hace despues de que el SAT responde, nunca antes: si se devolviera primero
  y la cancelacion se rechazara, el inventario quedaria inflado.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from app.models.inventory_ledger import InventoryLedger
from app.models.invoice import Invoice
from app.models.invoice_cancellation import InvoiceCancellation
from app.models.session import transaction_context
from app.services.inventory_service import apply_movement_in_session
from app.utils.errors import AppError


# c_MotivoCancelacion
CANCELLATION_MOTIVES = {
    "01": "Comprobante emitido con errores con relacion",
    "02": "Comprobante emitido con errores sin relacion",
    "03": "No se llevo a cabo la operacion",
    "04": "Operacion nominativa relacionada en una factura global",
}

# El unico motivo que sustituye un comprobante por otro.
MOTIVE_REQUIRING_SUBSTITUTION = "01"

# Estados de la solicitud.
REQUESTED = "solicitada"
IN_PROGRESS = "en_proceso"
CANCELLED = "cancelado"
REJECTED = "rechazado"

RESOLVED_STATUSES = {CANCELLED, REJECTED}
# Desde estos estados no se puede volver a solicitar.
BLOCKING_STATUSES = {REQUESTED, IN_PROGRESS, CANCELLED}

UUID_LENGTH = 36


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _authorize(invoice, user_data):
    if not invoice.id_proyect:
        raise AppError("errors.resource_scope_missing", 409)
    unrestricted = bool(user_data.get("is_superuser") or user_data.get("is_bootstrap_admin"))
    actor_project = user_data.get("id_proyect") or user_data.get("project_id")
    if not unrestricted and str(actor_project) != str(invoice.id_proyect):
        raise AppError("errors.permission_denied", 403)


def _load_invoice(db, invoice_id, user_data) -> Invoice:
    invoice = db.get(Invoice, int(invoice_id))
    if not invoice or invoice.deletion_date is not None:
        raise AppError("errors.resource_not_found", 404)
    _authorize(invoice, user_data)
    return invoice


def _cancellations(db, invoice_id):
    return db.scalars(
        select(InvoiceCancellation)
        .where(InvoiceCancellation.id_invoice == int(invoice_id))
        .order_by(InvoiceCancellation.id_invoice_cancellation)
    ).all()


def _blocking_cancellation(db, invoice_id):
    """La solicitud vigente que impide pedir otra, si la hay."""
    for solicitud in _cancellations(db, invoice_id):
        if solicitud.status in BLOCKING_STATUSES:
            return solicitud
    return None


def _validate_motive(payload) -> tuple[str, str | None]:
    motive = str(payload.get("motive") or "").strip()
    if motive not in CANCELLATION_MOTIVES:
        raise AppError(
            "errors.cancellation_motive_invalid",
            400,
            {"field": "motive", "allowed": sorted(CANCELLATION_MOTIVES)},
        )

    substitution = str(payload.get("substitution_uuid") or "").strip().upper() or None
    if motive == MOTIVE_REQUIRING_SUBSTITUTION and not substitution:
        raise AppError(
            "errors.cancellation_substitution_required",
            400,
            {"field": "substitution_uuid", "motive": motive},
        )
    if motive != MOTIVE_REQUIRING_SUBSTITUTION and substitution:
        raise AppError(
            "errors.cancellation_substitution_not_allowed",
            400,
            {"field": "substitution_uuid", "motive": motive},
        )
    if substitution and len(substitution) != UUID_LENGTH:
        raise AppError(
            "errors.cancellation_substitution_invalid",
            400,
            {"field": "substitution_uuid"},
        )
    return motive, substitution


def _validate_substitution_exists(db, invoice, substitution):
    """El comprobante que sustituye tiene que existir y estar timbrado."""
    if not substitution:
        return
    reemplazo = db.scalars(
        select(Invoice).where(Invoice.folio_fiscal == substitution)
    ).first()
    if reemplazo is None:
        raise AppError(
            "errors.cancellation_substitution_not_found",
            409,
            {"substitution_uuid": substitution},
        )
    if reemplazo.id_invoice == invoice.id_invoice:
        raise AppError(
            "errors.cancellation_substitution_is_same_invoice",
            409,
            {"substitution_uuid": substitution},
        )


def _require_stamped(invoice):
    if not str(invoice.folio_fiscal or "").strip():
        raise AppError(
            "errors.cancellation_requires_stamped_invoice",
            409,
            {"invoice_status": invoice.invoice_status},
        )


def preview_cancellation(invoice_id, payload, user_data) -> dict:
    """Si la factura se puede cancelar y con que consecuencias."""
    payload = payload or {}
    with transaction_context() as db:
        invoice = _load_invoice(db, invoice_id, user_data)
        solicitudes = _cancellations(db, invoice.id_invoice)
        vigente = _blocking_cancellation(db, invoice.id_invoice)
        timbrada = bool(str(invoice.folio_fiscal or "").strip())

        lineas = {str(linea.id_invoice_material_service) for linea in _invoice_lines(db, invoice.id_invoice)}
        a_revertir = db.scalars(
            select(InventoryLedger)
            .where(InventoryLedger.reference_type == "invoice_line")
            .where(InventoryLedger.reference_id.in_(lineas or {""}))
        ).all()

        return {
            "id_invoice": invoice.id_invoice,
            "folio_fiscal": invoice.folio_fiscal,
            "invoice_status": invoice.invoice_status,
            "is_stamped": timbrada,
            "motives": CANCELLATION_MOTIVES,
            "requires_substitution": [MOTIVE_REQUIRING_SUBSTITUTION],
            "current_request": vigente.serialize() if vigente else None,
            "history": [s.serialize() for s in solicitudes],
            "inventory_movements_to_reverse": len(a_revertir),
            # Cuantos abonos se van a dar de baja con la cancelacion. Se avisa
            # antes: cancelar una factura con abonos registrados es una decision
            # contable, y enterarse despues no sirve de nada.
            "payments_to_cancel": len(_abonos_vigentes(db, invoice)),
            "can_request": timbrada and vigente is None,
        }


def _invoice_lines(db, invoice_id):
    from app.models.invoice_material_service import InvoiceMaterialService

    return db.scalars(
        select(InvoiceMaterialService)
        .where(InvoiceMaterialService.id_invoice == int(invoice_id))
        .where(InvoiceMaterialService.deletion_date.is_(None))
    ).all()


def _abonos_vigentes(db, invoice) -> list:
    """Los abonos que la cancelacion daria de baja."""
    from app.models.invoice_payment import InvoicePayment
    from app.services.invoice_payment_service import CANCELLED as ABONO_CANCELADO

    return db.scalars(
        select(InvoicePayment).where(
            InvoicePayment.id_invoice == invoice.id_invoice,
            InvoicePayment.status != ABONO_CANCELADO,
            InvoicePayment.deletion_date.is_(None),
        )
    ).all()


def _cancelar_abonos(db, invoice) -> list[dict]:
    """Da de baja los abonos de una factura que dejo de existir.

    Por que hace falta
    ------------------
    Medido antes de esto: se timbra una factura de 1160 en parcialidades, se
    registra un abono de 500, se cancela la factura -y se cancelaba sin una
    queja- y el estado de cuenta seguia diciendo "saldo 660" sobre una factura
    que fiscalmente ya no existe. Las cuentas por cobrar contaban dinero de
    facturas canceladas.

    Por que se cancelan en vez de impedir la cancelacion
    ----------------------------------------------------
    No hay forma de anular un abono por separado -no existe la ruta-, asi que
    bloquear la cancelacion cuando hay abonos deja al usuario sin salida: no
    puede cancelar la factura ni quitar el abono. Los abonos son de la factura;
    si ella se cancela, ellos no pueden seguir vigentes.

    El estado `cancelado` ya existia y el propio servicio de pagos ya lo excluye
    del saldo y del listado; lo que faltaba era que alguien lo marcara.

    Lo que NO se hace es borrarlos. Un abono cancelado es historia contable: se
    cobro y despues se revirtio, y eso hay que poder verlo.
    """
    from app.models.invoice_payment import InvoicePayment
    from app.services.invoice_payment_service import CANCELLED as ABONO_CANCELADO

    abonos = db.scalars(
        select(InvoicePayment).where(
            InvoicePayment.id_invoice == invoice.id_invoice,
            InvoicePayment.status != ABONO_CANCELADO,
            InvoicePayment.deletion_date.is_(None),
        )
    ).all()
    for abono in abonos:
        abono.status = ABONO_CANCELADO
    if abonos:
        db.flush()
    return [a.serialize() for a in abonos]


def _reverse_inventory(db, invoice, user_data, cancellation) -> list[dict]:
    """Devuelve al almacen lo que esta factura habia movido.

    Se recorre el libro buscando los renglones que nacieron de las partidas de
    esta factura, y se escribe el movimiento contrario. La llave se deriva de
    la cancelacion, asi que repetirla no devuelve dos veces.
    """
    lineas = {str(linea.id_invoice_material_service) for linea in _invoice_lines(db, invoice.id_invoice)}
    if not lineas:
        return []

    originales = db.scalars(
        select(InventoryLedger)
        .where(InventoryLedger.reference_type == "invoice_line")
        .where(InventoryLedger.reference_id.in_(lineas))
        .order_by(InventoryLedger.id_inventory_ledger)
    ).all()

    revertidos = []
    for original in originales:
        contrario = -int(original.quantity_delta)
        movimiento, _ = apply_movement_in_session(
            db,
            original.id_product,
            user_data,
            # Lo que salio por una venta vuelve como devolucion; lo que entro
            # por una compra sale como salida.
            movement_type="return" if contrario > 0 else "issue",
            quantity_delta=contrario,
            idempotency_key=f"cancel-{cancellation.id_invoice_cancellation}-ledger-{original.id_inventory_ledger}",
            id_location=original.id_location,
            reference_type="invoice_line",
            reference_id=original.reference_id,
            reason=f"Reverso por cancelacion de la factura {invoice.id_invoice}",
        )
        revertidos.append(movimiento)
    return revertidos


def request_cancellation(invoice_id, payload, user_data, provider=None) -> dict:
    """Solicita al SAT la cancelacion de un comprobante timbrado."""
    payload = payload or {}
    key = str(payload.get("idempotency_key") or "").strip()
    if not key or len(key) > 100:
        raise AppError("errors.invalid_field", 400, {"field": "idempotency_key"})

    motive, substitution = _validate_motive(payload)

    from app.services.stamping import configured_provider

    provider = provider or configured_provider()

    with transaction_context() as db:
        previa = db.scalars(
            select(InvoiceCancellation).where(InvoiceCancellation.idempotency_key == key)
        ).first()
        if previa:
            if previa.id_invoice != int(invoice_id):
                raise AppError("errors.idempotency_conflict", 409)
            return {"cancellation": previa.serialize(), "inventory": [], "created": False}

        invoice = _load_invoice(db, invoice_id, user_data)
        _require_stamped(invoice)

        vigente = _blocking_cancellation(db, invoice.id_invoice)
        if vigente is not None:
            raise AppError(
                "errors.cancellation_already_requested",
                409,
                {"status": vigente.status, "id_invoice_cancellation": vigente.id_invoice_cancellation},
            )
        _validate_substitution_exists(db, invoice, substitution)

        solicitud = InvoiceCancellation(
            id_invoice=invoice.id_invoice,
            id_proyect=invoice.id_proyect,
            motive=motive,
            substitution_uuid=substitution,
            status=REQUESTED,
            provider=provider.name,
            reason=str(payload.get("reason") or "").strip()[:300] or None,
            idempotency_key=key,
            created_by=int(user_data.get("id_user") or 0),
        )
        db.add(solicitud)
        db.flush()

        resultado = provider.cancel(
            {
                "uuid": invoice.folio_fiscal,
                "motive": motive,
                "substitution_uuid": substitution,
                "issuer_rfc": invoice.nombre_emisor,
                "total": format(invoice.total or 0, "f") if invoice.total is not None else None,
            },
            key,
        )
        solicitud.status = resultado.status
        solicitud.provider_reference = resultado.reference
        solicitud.acknowledgement = resultado.acknowledgement
        solicitud.response_metadata = resultado.metadata
        solicitud.error_code = resultado.error_code
        if resultado.status in RESOLVED_STATUSES:
            solicitud.resolved_date = _now()

        movimientos = []
        abonos_cancelados = []
        if resultado.status == CANCELLED:
            invoice.invoice_status = "cancelada"
            # El almacen se devuelve DESPUES de que el SAT confirma. Al reves,
            # una cancelacion rechazada dejaria el inventario inflado.
            movimientos = _reverse_inventory(db, invoice, user_data, solicitud)
            # Y con el mismo criterio, los abonos: una factura cancelada no
            # puede seguir teniendo saldo por cobrar.
            abonos_cancelados = _cancelar_abonos(db, invoice)

        db.flush()
        return {
            "cancellation": solicitud.serialize(),
            "inventory": movimientos,
            "payments_cancelled": abonos_cancelados,
            "created": True,
        }


def refresh_cancellation(cancellation_id, user_data, provider=None) -> dict:
    """Consulta al SAT si una solicitud en proceso ya se resolvio."""
    from app.services.stamping import configured_provider

    provider = provider or configured_provider()

    with transaction_context() as db:
        solicitud = db.get(InvoiceCancellation, int(cancellation_id))
        if not solicitud:
            raise AppError("errors.resource_not_found", 404)
        invoice = _load_invoice(db, solicitud.id_invoice, user_data)

        if solicitud.status in RESOLVED_STATUSES:
            return {"cancellation": solicitud.serialize(), "inventory": [], "changed": False}

        resultado = provider.cancellation_status(solicitud.provider_reference or invoice.folio_fiscal)
        if resultado.status == solicitud.status:
            return {"cancellation": solicitud.serialize(), "inventory": [], "changed": False}

        solicitud.status = resultado.status
        solicitud.acknowledgement = resultado.acknowledgement or solicitud.acknowledgement
        solicitud.response_metadata = resultado.metadata or solicitud.response_metadata
        solicitud.error_code = resultado.error_code
        movimientos = []
        abonos_cancelados = []
        if resultado.status in RESOLVED_STATUSES:
            solicitud.resolved_date = _now()
        if resultado.status == CANCELLED:
            invoice.invoice_status = "cancelada"
            movimientos = _reverse_inventory(db, invoice, user_data, solicitud)
            abonos_cancelados = _cancelar_abonos(db, invoice)
        db.flush()
        return {"cancellation": solicitud.serialize(), "inventory": movimientos,
                "payments_cancelled": abonos_cancelados, "changed": True}
