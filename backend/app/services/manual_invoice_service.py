from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from datetime import datetime, timezone

from sqlalchemy import select

from app.models import CustomerSupplier, Invoice, InvoiceMaterialService, Proyect, Status
from app.models.session import transaction_context
from app.services.invoice_builder import normalize_cfdi_type, normalize_cfdi_use
from app.services.invoice_catalogs import OBJETO_IMP_CON_DESGLOSE, TASAS_IVA_TRASLADO
from app.utils.errors import AppError


MONEY = Decimal('0.01')
UNIT_PRICE = Decimal('0.000001')
RATE = Decimal('0.0001')


def _decimal(value, field: str) -> Decimal:
    try:
        number = Decimal(str(value if value not in (None, '') else '0'))
    except InvalidOperation as exc:
        raise AppError('errors.invalid_field', 400, {'field': field}) from exc
    # NaN e Infinity no son importes: revientan mas adelante con un 500.
    if not number.is_finite():
        raise AppError('errors.invalid_field', 400, {'field': field})
    return number


def _percentage(value, field: str) -> Decimal:
    percentage = _decimal(value, field)
    if percentage < 0 or percentage > 100:
        raise AppError('errors.invalid_field', 400, {'field': field})
    return percentage / Decimal('100')


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)


def _unit_price(value: Decimal) -> Decimal:
    return value.quantize(UNIT_PRICE, rounding=ROUND_HALF_UP).normalize()


def _rate(value: Decimal) -> Decimal:
    return value.quantize(RATE, rounding=ROUND_HALF_UP)


# iva_tipo -> (tasa, ObjetoImp forzado, es_exento).
# 'exento' y '0' no son lo mismo para el SAT: el exento se declara con
# TipoFactor="Exento" (sin TasaOCuota ni Importe) y la tasa 0% con
# TipoFactor="Tasa" y TasaOCuota="0.000000".
IVA_TYPES = {
    '16': (Decimal('16'), '02', False),
    '8': (Decimal('8'), '02', False),
    '0': (Decimal('0'), '02', False),
    'tasa_0': (Decimal('0'), '02', False),
    'exento': (Decimal('0'), '02', True),
    'sin_iva': (Decimal('0'), '01', False),
    'no_objeto': (Decimal('0'), '01', False),
}


def _tipo_de_cambio_por_omision(payload: dict):
    """El tipo de cambio capturado, o el valor que obliga a capturarlo.

    En pesos, 1. En moneda extranjera sin capturar, 0: el validador lee el cero
    como "no capturado" y lo rechaza, que es lo que hace falta para que nadie
    timbre dolares a la par sin darse cuenta.
    """
    capturado = payload.get('type_exchange_rate') or payload.get('tipo_cambio')
    if capturado not in (None, ''):
        if _decimal(capturado, 'type_exchange_rate') < 0:
            raise AppError('errors.invalid_field', 400, {'field': 'type_exchange_rate'})
        return capturado
    moneda = str(payload.get('currency') or payload.get('moneda') or 'MXN').strip().upper()
    return 1 if moneda in ('MXN', 'XXX', '') else 0


def preview_manual_invoice(payload: dict) -> dict:
    concepts = payload.get('concepts') or payload.get('conceptos') or payload.get('items') or []
    errors = []
    if not concepts:
        errors.append('manual_invoice.concepts_required')

    iva_type = str(payload.get('iva_tipo') or '').strip().lower()
    iva_value, forced_tax_object, forced_exempt = IVA_TYPES.get(
        iva_type, (payload.get('iva_rate', payload.get('tax_rate', 16)), None, None)
    )
    default_iva_rate = _percentage(iva_value, 'iva_rate')
    default_isr_rate = _percentage(payload.get('isr_ret_rate', 0), 'isr_ret_rate')
    default_iva_ret_rate = _percentage(payload.get('iva_ret_rate', 0), 'iva_ret_rate')
    subtotal = Decimal('0')
    discount_total = Decimal('0')
    iva_total = Decimal('0')
    isr_retention_total = Decimal('0')
    iva_retention_total = Decimal('0')
    normalized = []

    for index, concept in enumerate(concepts):
        description = str(concept.get('description') or concept.get('descripcion') or '').strip()
        sat_product_key = str(concept.get('sat_product_key') or concept.get('clave_prod_serv') or '').strip()
        sat_unit_key = str(concept.get('sat_unit_key') or concept.get('clave_unidad') or '').strip()
        quantity = _decimal(concept.get('quantity', concept.get('cantidad')), f'concepts.{index}.quantity')
        unit_price = _decimal(concept.get('unit_price', concept.get('gross_price', concept.get('valor_unitario'))), f'concepts.{index}.unit_price')
        discount = _decimal(concept.get('discount', concept.get('descuento', 0)), f'concepts.{index}.discount')
        if not description:
            errors.append(f'manual_invoice.concepts.{index}.description_required')
        if not sat_product_key:
            errors.append(f'manual_invoice.concepts.{index}.sat_product_key_required')
        if not sat_unit_key:
            errors.append(f'manual_invoice.concepts.{index}.sat_unit_key_required')
        if quantity <= 0 or unit_price < 0 or discount < 0:
            errors.append(f'manual_invoice.concepts.{index}.invalid_amount')

        # El Importe del concepto se redondea aqui, igual que en el XML: el
        # SubTotal del comprobante es la suma de estos importes ya redondeados
        # (Anexo 20). Sumar sin redondear y redondear el total al final produce
        # diferencias de centavos que el PAC rechaza.
        line_subtotal = _money(quantity * unit_price)
        discount = _money(discount)
        if discount > line_subtotal:
            errors.append(f'manual_invoice.concepts.{index}.discount_exceeds_subtotal')
            taxable_base = Decimal('0')
        else:
            taxable_base = line_subtotal - discount

        tax_object = str(forced_tax_object or concept.get('tax_object') or concept.get('objeto_imp') or '02')
        breaks_down_taxes = tax_object in OBJETO_IMP_CON_DESGLOSE
        taxable = bool(concept.get('tax_applicable', breaks_down_taxes)) and breaks_down_taxes
        is_exempt = bool(concept.get('iva_exempt') if forced_exempt is None else forced_exempt) and taxable
        iva_rate = _percentage(concept.get('iva_rate', default_iva_rate * 100), f'concepts.{index}.iva_rate') if taxable and not is_exempt else Decimal('0')
        isr_rate = _percentage(concept.get('isr_ret_rate', default_isr_rate * 100), f'concepts.{index}.isr_ret_rate') if taxable else Decimal('0')
        iva_ret_rate = _percentage(concept.get('iva_ret_rate', default_iva_ret_rate * 100), f'concepts.{index}.iva_ret_rate') if taxable else Decimal('0')
        # La tasa de IVA se valida ya en la vista previa: es mejor avisarlo al
        # capturar que dejarlo salir en el timbrado.
        if taxable and not is_exempt and iva_rate not in TASAS_IVA_TRASLADO:
            errors.append(f'manual_invoice.concepts.{index}.iva_rate_not_in_catalog')
        line_iva = _money(taxable_base * iva_rate)
        line_isr_retention = _money(taxable_base * isr_rate)
        line_iva_retention = _money(taxable_base * iva_ret_rate)
        line_total = taxable_base + line_iva - line_isr_retention - line_iva_retention

        subtotal += line_subtotal
        discount_total += discount
        iva_total += line_iva
        isr_retention_total += line_isr_retention
        iva_retention_total += line_iva_retention
        normalized.append({
            'description': description,
            'quantity': str(quantity),
            # ValorUnitario admite hasta 6 decimales; redondearlo a 2 rompia
            # la igualdad Importe = Cantidad * ValorUnitario.
            'unit_price': str(_unit_price(unit_price)),
            'discount': str(discount),
            'amount': str(line_subtotal),
            'sat_product_key': sat_product_key,
            'sat_unit_key': sat_unit_key,
            'tax_object': tax_object,
            'iva_exempt': is_exempt,
            'iva_rate': str(_rate(iva_rate * 100)),
            'isr_ret_rate': str(_rate(isr_rate * 100)),
            'iva_ret_rate': str(_rate(iva_ret_rate * 100)),
            'iva': str(line_iva),
            'isr_retention': str(line_isr_retention),
            'iva_retention': str(line_iva_retention),
            'total': str(_money(line_total)),
        })

    total = subtotal - discount_total + iva_total - isr_retention_total - iva_retention_total
    if total < 0:
        errors.append('manual_invoice.total_negative')
    return {
        'concepts': normalized,
        'errors': errors,
        'warnings': [],
        'can_create': not errors,
        'subtotal': str(_money(subtotal)),
        'discount': str(_money(discount_total)),
        'iva': str(_money(iva_total)),
        'isr_retention': str(_money(isr_retention_total)),
        'iva_retention': str(_money(iva_retention_total)),
        'total': str(_money(total)),
    }


def _required_int(value, field: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise AppError('errors.invalid_field', 400, {'field': field}) from exc
    if parsed <= 0:
        raise AppError('errors.invalid_field', 400, {'field': field})
    return parsed


def _date_time(value, field: str) -> datetime:
    if not value:
        return datetime.now(timezone.utc).replace(tzinfo=None)
    try:
        return datetime.fromisoformat(str(value).replace('Z', '+00:00')).replace(tzinfo=None)
    except ValueError as exc:
        raise AppError('errors.invalid_field', 400, {'field': field}) from exc


def _load_context(db, payload: dict, user_data: dict):
    project_id = _required_int(payload.get('id_proyect'), 'id_proyect')
    customer_id = _required_int(payload.get('id_customer_supplier'), 'id_customer_supplier')
    issuer_id = _required_int(payload.get('id_issuer_customer_supplier'), 'id_issuer_customer_supplier')
    project = db.get(Proyect, project_id)
    customer = db.get(CustomerSupplier, customer_id)
    issuer = db.get(CustomerSupplier, issuer_id)
    if not project or not customer or not issuer:
        raise AppError('errors.resource_not_found', 404)

    unrestricted = bool(user_data.get('is_superuser') or user_data.get('is_bootstrap_admin'))
    actor_project = user_data.get('id_proyect') or user_data.get('project_id')
    if not unrestricted and str(actor_project) != str(project.id_proyect):
        raise AppError('errors.resource_not_found', 404)

    status_id = payload.get('id_status')
    status = db.get(Status, _required_int(status_id, 'id_status')) if status_id else db.scalars(
        select(Status).order_by(Status.id_status.asc())
    ).first()
    if not status:
        raise AppError('manual_invoice.status_required', 409)
    return project, customer, issuer, status


def validate_manual_invoice_context(payload: dict, user_data: dict) -> None:
    with transaction_context() as db:
        _load_context(db, payload, user_data)


def create_manual_invoice(payload: dict, user_data: dict) -> dict:
    preview = preview_manual_invoice(payload)
    if not preview['can_create']:
        raise AppError('manual_invoice.validation_failed', 400, {'errors': preview['errors']})

    actor_id = _required_int(user_data.get('id_user'), 'id_user')
    concepts = payload.get('concepts') or payload.get('conceptos') or payload.get('items') or []
    with transaction_context() as db:
        project, customer, issuer, status = _load_context(db, payload, user_data)
        emitted_at = _date_time(payload.get('date_emision'), 'date_emision')
        expires_at = _date_time(payload.get('date_expiration'), 'date_expiration')
        if expires_at < emitted_at:
            raise AppError('validations.invoice.date_expiration.after_emision', 400)

        invoice = Invoice(
            date_emision=emitted_at,
            date_expiration=expires_at,
            subtotal=Decimal(preview['subtotal']),
            descuento=Decimal(preview['discount']),
            tax=Decimal(preview['iva']),
            isr_retention=Decimal(preview['isr_retention']),
            iva_retention=Decimal(preview['iva_retention']),
            total=Decimal(preview['total']),
            invoice_status='pendiente',
            payment_method=str(payload.get('forma_pago') or ''),
            forma_pago=str(payload.get('forma_pago') or ''),
            metodo_pago=str(payload.get('metodo_pago') or '').strip().upper(),
            uso_cfdi=normalize_cfdi_use(payload.get('uso_cfdi')),
            note=str(payload.get('note') or payload.get('notas') or '')[:300] or None,
            id_customer_supplier=customer.id_customer_supplier,
            id_issuer_customer_supplier=issuer.id_customer_supplier,
            id_proyect=project.id_proyect,
            internationalization='local',
            currency=str(payload.get('currency') or payload.get('moneda') or 'MXN')[:30],
            # El tipo de cambio NO se rellena con 1 cuando la moneda es
            # extranjera.
            #
            # Con el 1 por omision, elegir USD y no tocar el campo daba una
            # factura de 116 USD "a 1 peso por dolar", que el validador solo
            # marcaba como AVISO y por tanto se podia timbrar: el SAT leia 116
            # pesos por algo que cuesta unos dos mil. Medido: can_stamp = True.
            #
            # Dejandolo en cero -que es como el validador lee "no capturado"-
            # el mismo validador lo convierte en error y pide el dato. El 1
            # explicito se respeta: una moneda a la par es raro pero legal.
            type_exchange_rate=_decimal(
                _tipo_de_cambio_por_omision(payload), 'type_exchange_rate'),
            tax_certification_supplier=_required_int(payload.get('tax_certification_supplier') or issuer.id_customer_supplier, 'tax_certification_supplier'),
            id_status=status.id_status,
            created_by=actor_id,
            nombre_emisor=str(issuer.name or '')[:150],
            lugar_expedicion=str(payload.get('lugar_expedicion') or issuer.postal_code or '')[:120],
            # c_TipoDeComprobante: 'I' = Ingreso. Guardar la etiqueta 'factura'
            # dejaba el registro fuera del catalogo del SAT.
            tipo_de_comprobante=normalize_cfdi_type(payload.get('tipo_de_comprobante')),
            rfc_receptor=str(payload.get('rfc') or customer.tax_id or '')[:20],
            nombre_receptor=str(payload.get('razon_social_fiscal') or customer.name or '')[:150],
            regimen_fiscal_receptor=str(payload.get('regimen_fiscal') or customer.fiscal_type or '')[:100],
            domicilio_fiscal_receptor=str(payload.get('cp_fiscal') or customer.postal_code or '')[:250],
            exportacion=str(payload.get('exportacion') or '01')[:50],
            # Serie por defecto de la empresa emisora si la factura no trae
            # una explicita -- mismo criterio que lugar_expedicion arriba.
            serie_csd=str(payload.get('series') or payload.get('serie') or issuer.serie_csd or '')[:25] or None,
            folio=str(payload.get('folio') or '')[:30] or None,
            condiciones_pago=str(payload.get('condiciones_pago') or '')[:100] or None,
            apply_tax=Decimal(preview['iva']) > 0,
            tax_rate=_decimal(payload.get('iva_rate', payload.get('tax_rate', 16)), 'iva_rate'),
            commercial_terms=str(payload.get('commercial_terms') or '')[:500] or None,
            manual_capture=True,
            # De que venta nace, cuando no nace aqui. Se fija al crear y no
            # despues: una factura que existio un instante sin su origen es una
            # factura que en ese instante habria movido el inventario.
            source_module=str(payload.get('source_module') or '').strip() or None,
            source_reference=str(payload.get('source_reference') or '').strip()[:80] or None,
        )
        db.add(invoice)
        db.flush()

        line_status_id = _required_int(payload.get('line_id_status') or status.id_status, 'line_id_status')
        buyer_id = _required_int(payload.get('id_buyer') or actor_id, 'id_buyer')
        for original, normalized in zip(concepts, preview['concepts']):
            line = InvoiceMaterialService(
                id_invoice=invoice.id_invoice,
                id_material=original.get('id_material') or None,
                id_service=original.get('id_service') or None,
                id_product=original.get('id_product') or None,
                id_unit=original.get('id_unit') or None,
                # Solo lo usa el flujo de nota de credito -de que renglon de
                # la factura original viene esta partida-. Una factura o
                # cotizacion normal nunca manda este campo.
                id_original_line=original.get('id_original_line') or None,
                invoice_material_service_description=normalized['description'][:200],
                is_directly_related_to_product_service_creation=False,
                id_authorized=actor_id,
                id_status=line_status_id,
                id_buyer=buyer_id,
                id_customer_supplier=customer.id_customer_supplier,
                gross_price=Decimal(normalized['unit_price']),
                quantity=Decimal(normalized['quantity']),
                iva_exempt=bool(normalized['iva_exempt']),
                created_by=actor_id,
                line_type=str(original.get('line_type') or 'custom'),
                tax_applicable=normalized['tax_object'] != '01',
                line_tax=Decimal(normalized['iva']),
                line_total=Decimal(normalized['total']),
                authorization_status='authorized',
                authorization_date=datetime.now(timezone.utc).replace(tzinfo=None),
                discount=Decimal(normalized['discount']),
                sat_product_key=normalized['sat_product_key'],
                sat_unit_key=normalized['sat_unit_key'],
                tax_object=normalized['tax_object'],
                tax_rate=Decimal(normalized['iva_rate']),
                isr_retention_rate=Decimal(normalized['isr_ret_rate']),
                iva_retention_rate=Decimal(normalized['iva_ret_rate']),
            )
            db.add(line)
        db.flush()
        return {
            'invoice': invoice.serialize(),
            'concepts': preview['concepts'],
            'message_key': 'success.manual_invoice_created',
        }
