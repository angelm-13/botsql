"""Timbrado real del complemento de pago (REP) de un abono.

`invoice_payment_service.build_payment_complement` solo arma el payload (un
preview de solo lectura); este modulo es el que de verdad timbra: crea el
comprobante de tipo P, se lo manda al PAC, y deja todo persistido -- o nada,
si algo falla.

Formato del payload confirmado con timbrado real contra el sandbox de
Facturama (no solo con su guia) en la sesion que retomo esta fase: ver
`CLAUDE.md` seccion "Fase 3 - spike en vivo".
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select

from app.models.invoice import Invoice
from app.models.invoice_payment import InvoicePayment
from app.models.session import transaction_context
from app.models.stamping_operation import StampingOperation
from app.services.cfdi_validation import validate_cfdi_xml
from app.services.cfdi_xml import parse_cfdi
from app.services.cfdi_xml_store import save_cfdi_xml
from app.services.invoice_payment_service import (
    CANCELLED,
    STAMPED,
    UNDEFINED_PAYMENT_FORM,
    _complement_payload,
    _load_invoice,
)
from app.services.stamping import configured_provider
from app.utils.errors import AppError


def stamp_payment_complement(payment_id, idempotency_key, user_data, provider=None):
    """Timbra el REP de un abono ya registrado. Idempotente, con rollback
    atomico ante cualquier excepcion -- mismo patron que `stamp_invoice`.
    """
    key = str(idempotency_key or "").strip()
    if not key or len(key) > 100:
        raise AppError("errors.invalid_field", 400, {"field": "idempotency_key"})
    provider = provider or configured_provider()

    with transaction_context() as db:
        previous = db.scalars(
            select(StampingOperation).where(StampingOperation.idempotency_key == key)
        ).first()
        if previous:
            abono_actual = db.get(InvoicePayment, int(payment_id))
            if not abono_actual:
                raise AppError("errors.resource_not_found", 404)
            # Solo se puede verificar contra que abono era esta llave una vez
            # que el REP existe de verdad (abono.id_payment_invoice). Antes de
            # eso (un reintento sobre un intento previo rechazado o incierto)
            # se confia en la llave, igual que hace register_payment.
            if abono_actual.id_payment_invoice and abono_actual.id_payment_invoice != previous.id_invoice:
                raise AppError("errors.idempotency_conflict", 409)
            return previous.serialize(), False

        abono = db.get(InvoicePayment, int(payment_id))
        if not abono or abono.deletion_date is not None:
            raise AppError("errors.resource_not_found", 404)
        if abono.status == STAMPED:
            raise AppError("errors.payment_already_stamped", 409)
        if abono.status == CANCELLED:
            raise AppError("errors.payment_cancelled", 409)
        # Defensa en profundidad: register_payment ya rechaza forma_pago=99 al
        # capturar el abono, esto nunca deberia dispararse en el flujo normal.
        if abono.payment_form == UNDEFINED_PAYMENT_FORM:
            raise AppError("errors.payment_form_cannot_be_undefined", 400, {"field": "payment_form"})

        original = _load_invoice(db, abono.id_invoice, user_data)
        if not str(original.folio_fiscal or "").strip():
            raise AppError("errors.payment_requires_stamped_invoice", 409)

        payload = _complement_payload(db, abono, original)

        # El REP es un comprobante propio (tipo P), en ceros -- mismos campos
        # NOT NULL que cualquier factura manual (manual_invoice_service).
        complemento = Invoice(
            id_customer_supplier=original.id_customer_supplier,
            id_issuer_customer_supplier=original.id_issuer_customer_supplier,
            id_proyect=original.id_proyect,
            id_status=original.id_status,
            tax_certification_supplier=original.id_issuer_customer_supplier,
            created_by=int(user_data.get("id_user") or 0),
            apply_tax=False,
            tax_rate=Decimal("0"),
            manual_capture=False,
            subtotal=Decimal("0"),
            tax=Decimal("0"),
            total=Decimal("0"),
            currency=abono.currency,
            type_exchange_rate=abono.exchange_rate,
            tipo_de_comprobante="P",
            uso_cfdi="CP01",
            nombre_emisor=payload["issuer"]["name"],
            lugar_expedicion=payload["issuer"]["postal_code"],
            rfc_receptor=payload["receiver"]["rfc"],
            nombre_receptor=payload["receiver"]["name"],
            regimen_fiscal_receptor=payload["receiver"]["tax_regime"],
            domicilio_fiscal_receptor=payload["receiver"]["postal_code"],
            exportacion="01",
            invoice_status="pendiente",
        )
        db.add(complemento)
        db.flush()
        # Facturama exige Folio en cualquier comprobante bajo la cuenta
        # multiemisor, incluido el REP -- sin una serie propia para estos,
        # se usa el id interno, que ya es unico por construccion.
        complemento.folio = str(complemento.id_invoice)
        payload["folio"] = complemento.folio

        operation = StampingOperation(
            id_invoice=complemento.id_invoice,
            id_proyect=complemento.id_proyect,
            idempotency_key=key,
            provider=provider.name,
            status="processing",
            created_by=int(user_data.get("id_user") or 0),
        )
        db.add(operation)
        db.flush()

        result = provider.stamp_payment_complement(payload, key)
        operation.status = result.status
        operation.provider_reference = result.reference
        operation.response_metadata = result.metadata
        operation.error_code = result.error_code

        if result.status == "rejected":
            # A diferencia de `stamp_invoice` (donde la factura ya existia
            # antes del intento): aqui el comprobante tipo P se creo
            # especificamente para este intento. Un rechazo definitivo del
            # PAC significa que en Facturama no quedo nada -- asi que tampoco
            # debe quedar nada de este lado. Se deja que la excepcion
            # propague para que `transaction_context` revierta todo
            # (complemento + operacion incluidos), no solo se marque como
            # rechazado.
            raise AppError(
                "invoice.payment_complement_rejected",
                502,
                {"error_code": result.error_code, "response_metadata": result.metadata},
            )

        if result.status == "stamped":
            if not result.reference:
                raise AppError("invoice.stamping_missing_uuid", 502)
            complemento.invoice_status = "timbrada"
            complemento.folio_fiscal = result.reference
            complemento.certification_date = datetime.now(timezone.utc).replace(tzinfo=None)
            if result.xml:
                xml_bytes = result.xml.encode("utf-8") if isinstance(result.xml, str) else result.xml
                fiscal_data = parse_cfdi(xml_bytes)
                if fiscal_data["uuid"] != str(result.reference).upper():
                    raise AppError("invoice.stamping_uuid_mismatch", 502)
                document_errors = validate_cfdi_xml(xml_bytes)
                if document_errors:
                    operation.status = "rejected"
                    operation.error_code = "cfdi_document_invalid"
                    operation.response_metadata = {**(result.metadata or {}), "cfdi_errors": document_errors}
                    raise AppError("invoice.stamped_document_invalid", 502, {"errors": document_errors})
                save_cfdi_xml(db, complemento.id_invoice, result.xml)
                complemento.cfdi_code = fiscal_data["uuid"]
                complemento.no_certificado = fiscal_data.get("no_certificado")
                complemento.no_certificado_sat = fiscal_data.get("no_certificado_sat")
                complemento.sello_sat = fiscal_data.get("sello_sat")
                certified_at = fiscal_data.get("certification_date")
                if certified_at:
                    complemento.certification_date = datetime.fromisoformat(certified_at).replace(tzinfo=None)
            abono.id_payment_invoice = complemento.id_invoice
            abono.status = STAMPED
            abono.stamp_metadata = result.metadata

        # Si se llega aqui sin haber entrado a "stamped", el resultado fue
        # "uncertain" (timeout): a diferencia de "rejected", no se sabe si
        # Facturama de verdad lo proceso, asi que forzar rollback arriesgaria
        # un reintento que duplique el REP si si lo hizo. Se deja persistido
        # (complemento en "pendiente" + operacion en "uncertain") para
        # reconciliar despues -- mismo criterio que ya usa `stamp_invoice`.
        db.flush()
        return operation.serialize(), True
