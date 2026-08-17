from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from datetime import datetime, timezone

from sqlalchemy import select

from app.models import CustomerSupplier, Invoice, InvoiceMaterialService, Proyect, Status
from app.models.session import transaction_context
from app.utils.errors import AppError


MONEY = Decimal('0.01')


def _decimal(value, field: str) -> Decimal:
    try:
        return Decimal(str(value if value not in (None, '') else '0'))
    except InvalidOperation as exc:
        raise AppError('errors.invalid_field', 400, {'field': field}) from exc


def _percentage(value, field: str) -> Decimal:
    percentage = _decimal(value, field)
    if percentage < 0 or percentage > 100:
        raise AppError('errors.invalid_field', 400, {'field': field})
    return percentage / Decimal('100')


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)


def preview_manual_invoice(payload: dict) -> dict:
    concepts = payload.get('concepts') or payload.get('conceptos') or payload.get('items') or []
    errors = []
    if not concepts:
        errors.append('manual_invoice.concepts_required')

    default_iva_rate = _percentage(payload.get('iva_rate', payload.get('tax_rate', 16)), 'iva_rate')
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

        line_subtotal = quantity * unit_price
        if discount > line_subtotal:
            errors.append(f'manual_invoice.concepts.{index}.discount_exceeds_subtotal')
            taxable_base = Decimal('0')
        else:
            taxable_base = line_subtotal - discount

        taxable = bool(concept.get('tax_applicable', concept.get('objeto_imp', '02') != '01'))
        iva_rate = _percentage(concept.get('iva_rate', default_iva_rate * 100), f'concepts.{index}.iva_rate') if taxable else Decimal('0')
        isr_rate = _percentage(concept.get('isr_ret_rate', default_isr_rate * 100), f'concepts.{index}.isr_ret_rate') if taxable else Decimal('0')
        iva_ret_rate = _percentage(concept.get('iva_ret_rate', default_iva_ret_rate * 100), f'concepts.{index}.iva_ret_rate') if taxable else Decimal('0')
        line_iva = taxable_base * iva_rate
        line_isr_retention = taxable_base * isr_rate
        line_iva_retention = taxable_base * iva_ret_rate
        line_total = taxable_base + line_iva - line_isr_retention - line_iva_retention

        subtotal += line_subtotal
        discount_total += discount
        iva_total += line_iva
        isr_retention_total += line_isr_retention
        iva_retention_total += line_iva_retention
        normalized.append({
            'description': description,
            'quantity': str(quantity),
            'unit_price': str(_money(unit_price)),
            'discount': str(_money(discount)),
            'sat_product_key': sat_product_key,
            'sat_unit_key': sat_unit_key,
            'tax_object': str(concept.get('tax_object') or concept.get('objeto_imp') or ('02' if taxable else '01')),
            'iva_rate': str(_money(iva_rate * 100)),
            'isr_ret_rate': str(_money(isr_rate * 100)),
            'iva_ret_rate': str(_money(iva_ret_rate * 100)),
            'iva': str(_money(line_iva)),
            'isr_retention': str(_money(line_isr_retention)),
            'iva_retention': str(_money(line_iva_retention)),
            'total': str(_money(line_total)),
        })

    total = subtotal - discount_total + iva_total - isr_retention_total - iva_retention_total
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
            metodo_pago=str(payload.get('metodo_pago') or ''),
            uso_cfdi=str(payload.get('uso_cfdi') or ''),
            note=str(payload.get('note') or payload.get('notas') or '')[:300] or None,
            id_customer_supplier=customer.id_customer_supplier,
            id_issuer_customer_supplier=issuer.id_customer_supplier,
            id_proyect=project.id_proyect,
            internationalization='local',
            currency=str(payload.get('currency') or payload.get('moneda') or 'MXN')[:30],
            type_exchange_rate=_decimal(payload.get('type_exchange_rate') or 1, 'type_exchange_rate'),
            tax_certification_supplier=_required_int(payload.get('tax_certification_supplier') or issuer.id_customer_supplier, 'tax_certification_supplier'),
            id_status=status.id_status,
            created_by=actor_id,
            nombre_emisor=str(issuer.name or '')[:150],
            lugar_expedicion=str(payload.get('lugar_expedicion') or issuer.postal_code or '')[:120],
            tipo_de_comprobante='factura',
            rfc_receptor=str(customer.tax_id or '')[:20],
            nombre_receptor=str(customer.name or '')[:150],
            regimen_fiscal_receptor=str(payload.get('regimen_fiscal') or customer.fiscal_type or '')[:100],
            domicilio_fiscal_receptor=str(payload.get('cp_fiscal') or customer.postal_code or '')[:250],
            exportacion=str(payload.get('exportacion') or '01')[:50],
            folio=str(payload.get('folio') or '')[:30] or None,
            condiciones_pago=str(payload.get('condiciones_pago') or '')[:100] or None,
            apply_tax=Decimal(preview['iva']) > 0,
            tax_rate=_decimal(payload.get('iva_rate', payload.get('tax_rate', 16)), 'iva_rate'),
            commercial_terms=str(payload.get('commercial_terms') or '')[:500] or None,
            manual_capture=True,
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
                invoice_material_service_description=normalized['description'][:200],
                is_directly_related_to_product_service_creation=False,
                id_authorized=actor_id,
                id_status=line_status_id,
                id_buyer=buyer_id,
                id_customer_supplier=customer.id_customer_supplier,
                gross_price=Decimal(normalized['unit_price']),
                quantity=Decimal(normalized['quantity']),
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