"""Complemento de pago: los abonos de una factura en parcialidades.

Cuando el metodo de pago es PPD, la factura no acredita el cobro. Cada abono
exige su propio comprobante, de tipo P, con el complemento de pagos. Ese
comprobante tiene dos particularidades que suelen sorprender:

* va en ceros, porque el importe vive dentro del complemento y no en el cuerpo
  del comprobante;
* no lleva forma ni metodo de pago en el cuerpo, y su uso de CFDI es siempre
  CP01.

De cada abono se guarda el saldo que habia antes, lo que se paga y el saldo que
queda. Ese encadenamiento es lo que permite reconstruir el estado de cuenta, y
lo que hace que el sistema pueda rechazar un abono que exceda lo que se debe.

Un pago no se registra sobre una factura de contado (PUE): ahi el cobro ya
quedo acreditado con la factura misma.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from sqlalchemy import func, select

from app.models.invoice import Invoice
from app.models.invoice_payment import InvoicePayment
from app.models.session import transaction_context
from app.services.invoice_catalogs import FORMA_PAGO
from app.utils.errors import AppError


MONEY = Decimal("0.01")

# Metodo de pago que exige complemento. En PUE el cobro va en la propia factura.
DEFERRED_METHOD = "PPD"

# Estatus de factura sobre los que tiene sentido registrar un abono. Se incluye
# "pagada" a proposito: asi el intento de abonar de mas se rechaza con el
# mensaje preciso -que ya esta saldada- y no con uno generico sobre el estatus.
PAYABLE_STATUSES = {"timbrada", "pendiente", "parcial", "pagada"}

PENDING = "pendiente"
STAMPED = "timbrado"
CANCELLED = "cancelado"

# El SAT no admite "por definir" en un pago: si ya se cobro, se sabe como.
UNDEFINED_PAYMENT_FORM = "99"


def _money(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(MONEY, rounding=ROUND_HALF_UP)


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


def _payments(db, invoice_id):
    return db.scalars(
        select(InvoicePayment)
        .where(InvoicePayment.id_invoice == int(invoice_id))
        .where(InvoicePayment.deletion_date.is_(None))
        .where(InvoicePayment.status != CANCELLED)
        .order_by(InvoicePayment.instalment)
    ).all()


def _paid_so_far(db, invoice_id) -> Decimal:
    total = db.scalar(
        select(func.coalesce(func.sum(InvoicePayment.amount), 0))
        .where(InvoicePayment.id_invoice == int(invoice_id))
        .where(InvoicePayment.deletion_date.is_(None))
        .where(InvoicePayment.status != CANCELLED)
    )
    return _money(total)


def _parse_amount(value, field) -> Decimal:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise AppError("errors.invalid_field", 400, {"field": field}) from exc
    if amount <= 0:
        raise AppError("errors.payment_amount_must_be_positive", 400, {"field": field})
    return _money(amount)


def _parse_date(value, field):
    if not value:
        return _now()
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError as exc:
        raise AppError("errors.invalid_field", 400, {"field": field}) from exc


def _require_deferred_invoice(invoice):
    metodo = str(invoice.metodo_pago or "").strip().upper()
    if metodo != DEFERRED_METHOD:
        raise AppError(
            "errors.payment_requires_deferred_invoice",
            409,
            {"metodo_pago": metodo or None, "expected": DEFERRED_METHOD},
        )
    if str(invoice.invoice_status or "").strip().lower() not in PAYABLE_STATUSES:
        raise AppError(
            "errors.payment_invoice_status_not_allowed",
            409,
            {"invoice_status": invoice.invoice_status, "allowed": sorted(PAYABLE_STATUSES)},
        )


def _validate_payment_form(value) -> str:
    forma = str(value or "").strip()
    if forma not in FORMA_PAGO:
        raise AppError(
            "errors.payment_form_invalid",
            400,
            {"field": "payment_form", "allowed": sorted(FORMA_PAGO)},
        )
    if forma == UNDEFINED_PAYMENT_FORM:
        # Un pago ya ocurrio; decir "por definir" seria contradecirlo.
        raise AppError(
            "errors.payment_form_cannot_be_undefined",
            400,
            {"field": "payment_form"},
        )
    return forma


def invoice_statement(invoice_id, user_data) -> dict:
    """Estado de cuenta de la factura: lo pagado, lo que falta y cada abono."""
    with transaction_context() as db:
        invoice = _load_invoice(db, invoice_id, user_data)
        abonos = _payments(db, invoice.id_invoice)
        total = _money(invoice.total)
        pagado = _paid_so_far(db, invoice.id_invoice)
        metodo = str(invoice.metodo_pago or "").strip().upper()
        return {
            "id_invoice": invoice.id_invoice,
            "folio_fiscal": invoice.folio_fiscal,
            "metodo_pago": metodo or None,
            "requires_payment_complement": metodo == DEFERRED_METHOD,
            "total": format(total, "f"),
            "paid": format(pagado, "f"),
            "outstanding": format(total - pagado, "f"),
            "is_settled": pagado >= total > 0,
            "next_instalment": len(abonos) + 1,
            "payments": [abono.serialize() for abono in abonos],
        }


def register_payment(invoice_id, payload, user_data) -> dict:
    """Registra un abono y deja listo su comprobante de tipo P.

    El saldo anterior y el insoluto se calculan aqui, no se reciben: si los
    pusiera el llamador, dos abonos simultaneos podrian declarar el mismo saldo
    anterior y el estado de cuenta dejaria de cuadrar.
    """
    payload = payload or {}
    key = str(payload.get("idempotency_key") or "").strip()
    if not key or len(key) > 100:
        raise AppError("errors.invalid_field", 400, {"field": "idempotency_key"})

    amount = _parse_amount(payload.get("amount"), "amount")
    payment_form = _validate_payment_form(payload.get("payment_form"))
    paid_at = _parse_date(payload.get("paid_at"), "paid_at")
    # La moneda se normaliza aqui porque el guardia de idempotencia la compara,
    # y sin normalizar "mxn" y "MXN" pareceria dos peticiones distintas. Queda
    # en None cuando la peticion no la trae: entonces el abono hereda la de la
    # factura, y comparar contra un "MXN" supuesto marcaria como conflicto un
    # reintento legitimo sobre una factura en dolares.
    moneda = str(payload.get("currency") or "").strip()[:3].upper() or None

    with transaction_context() as db:
        previo = db.scalars(
            select(InvoicePayment).where(InvoicePayment.idempotency_key == key)
        ).first()
        if previo:
            # Una llave de idempotencia promete que repetir la MISMA peticion no
            # cobra dos veces. No promete nada sobre repetir la llave con otros
            # datos, y el guardia anterior solo comparaba la factura: abonar 100
            # con la llave "K" y despues 900 con la misma llave devolvia el abono
            # de 100 y contestaba que todo bien. Medido, y es lo peor que puede
            # pasar aqui: el cliente cree que abono 900 y la cuenta tiene 100.
            mismo = (
                previo.id_invoice == int(invoice_id)
                and Decimal(str(previo.amount)) == amount
                and (previo.payment_form or "") == (payment_form or "")
                and (moneda is None or (previo.currency or "") == moneda)
            )
            if not mismo:
                raise AppError(
                    "errors.idempotency_conflict",
                    409,
                    {
                        "idempotency_key": key,
                        "id_invoice_payment": previo.id_invoice_payment,
                        # Que se guardo con esa llave, para que quien reintento
                        # con datos corregidos vea que la llave ya estaba usada
                        # para otra cosa y no un 409 a secas.
                        "stored": {
                            "id_invoice": previo.id_invoice,
                            "amount": format(Decimal(str(previo.amount)), "f"),
                            "payment_form": previo.payment_form,
                            "currency": previo.currency,
                        },
                    },
                )
            return {"payment": previo.serialize(), "created": False}

        # Se bloquea la factura para que dos abonos a la vez no lean el mismo
        # saldo y acaben sumando mas de lo que se debe.
        invoice = db.scalars(
            select(Invoice).where(Invoice.id_invoice == int(invoice_id)).with_for_update()
        ).first()
        if not invoice or invoice.deletion_date is not None:
            raise AppError("errors.resource_not_found", 404)
        _authorize(invoice, user_data)
        _require_deferred_invoice(invoice)

        total = _money(invoice.total)
        if total <= 0:
            raise AppError("errors.payment_invoice_without_total", 409, {"total": format(total, "f")})

        pagado = _paid_so_far(db, invoice.id_invoice)
        saldo_anterior = total - pagado
        if saldo_anterior <= 0:
            raise AppError("errors.payment_invoice_already_settled", 409, {"total": format(total, "f")})
        if amount > saldo_anterior:
            raise AppError(
                "errors.payment_exceeds_outstanding",
                409,
                {"amount": format(amount, "f"), "outstanding": format(saldo_anterior, "f")},
            )

        parcialidad = len(_payments(db, invoice.id_invoice)) + 1
        abono = InvoicePayment(
            id_invoice=invoice.id_invoice,
            id_proyect=invoice.id_proyect,
            paid_at=paid_at,
            payment_form=payment_form,
            currency=moneda or str(invoice.currency or "MXN")[:3].upper(),
            exchange_rate=Decimal(str(payload.get("exchange_rate") or 1)),
            instalment=parcialidad,
            previous_balance=saldo_anterior,
            amount=amount,
            outstanding_balance=saldo_anterior - amount,
            operation_number=str(payload.get("operation_number") or "").strip()[:100] or None,
            note=str(payload.get("note") or "").strip()[:300] or None,
            status=PENDING,
            idempotency_key=key,
            created_by=int(user_data.get("id_user") or 0),
        )
        db.add(abono)
        db.flush()

        # La factura refleja si ya quedo saldada o va en parcialidades.
        invoice.invoice_status = "pagada" if abono.outstanding_balance == 0 else "parcial"
        db.flush()
        return {"payment": abono.serialize(), "created": True}


def build_payment_complement(payment_id, user_data) -> dict:
    """Datos del comprobante de tipo P que ampara un abono.

    Se devuelven ya con la forma que exige el complemento de pagos, para que el
    generador del XML no tenga que volver a interpretar nada.
    """
    with transaction_context() as db:
        abono = db.get(InvoicePayment, int(payment_id))
        if not abono or abono.deletion_date is not None:
            raise AppError("errors.resource_not_found", 404)
        invoice = _load_invoice(db, abono.id_invoice, user_data)
        if not str(invoice.folio_fiscal or "").strip():
            raise AppError("errors.payment_requires_stamped_invoice", 409)

        return {
            "id_invoice_payment": abono.id_invoice_payment,
            # El comprobante de pago va en ceros: el importe vive en el
            # complemento, no en el cuerpo.
            "cfdi_type": "P",
            "subtotal": "0",
            "total": "0",
            "cfdi_use": "CP01",
            "payment": {
                "paid_at": abono.paid_at.isoformat(),
                "payment_form": abono.payment_form,
                "currency": abono.currency,
                "exchange_rate": format(abono.exchange_rate, "f"),
                "amount": format(abono.amount, "f"),
                "operation_number": abono.operation_number,
            },
            "related_document": {
                "uuid": invoice.folio_fiscal,
                "series": invoice.fiscal_certify_serie or invoice.serie_csd,
                "folio": invoice.folio,
                "currency": abono.currency,
                "payment_method": DEFERRED_METHOD,
                "instalment": abono.instalment,
                "previous_balance": format(abono.previous_balance, "f"),
                "amount_paid": format(abono.amount, "f"),
                "outstanding_balance": format(abono.outstanding_balance, "f"),
            },
        }
