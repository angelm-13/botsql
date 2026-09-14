from __future__ import annotations

from decimal import Decimal

from app.services.invoice_catalogs import OBJETO_IMP_CON_DESGLOSE
from app.services.invoice_material_service_service import InvoiceMaterialServiceService


def build_xml_line_payloads(invoice: dict, concepts: list[dict], user_id: int | None = None) -> list[dict]:
    actor_id = int(user_id or invoice.get('created_by') or 1)
    payloads = []
    for concept in concepts or []:
        tax = Decimal(str(concept.get('tax') or 0))
        raw_rate = Decimal(str(concept.get('tax_rate') or 0))
        tax_rate = raw_rate * 100 if Decimal('0') < raw_rate <= Decimal('1') else raw_rate
        payloads.append({
            'id_invoice': invoice['id_invoice'],
            'invoice_material_service_description': str(concept.get('description') or 'Sin descripcion')[:200],
            'is_directly_related_to_product_service_creation': False,
            'id_authorized': actor_id,
            'id_status': invoice.get('id_status') or 1,
            'id_buyer': actor_id,
            'id_customer_supplier': invoice['id_customer_supplier'],
            'gross_price': concept.get('unit_price') or 0,
            'quantity': concept.get('quantity') or 1,
            'line_type': 'custom',
            # El objeto de impuesto es lo que manda: una partida exenta o a
            # tasa 0% si es objeto del impuesto aunque su importe sea cero.
            'tax_applicable': str(concept.get('tax_object') or '') in OBJETO_IMP_CON_DESGLOSE or tax > 0,
            'line_tax': tax,
            'line_total': concept.get('total') or concept.get('subtotal') or 0,
            'authorization_status': 'authorized',
            'discount': concept.get('discount') or 0,
            'sat_product_key': concept.get('sat_product_key') or '01010101',
            'sat_unit_key': concept.get('sat_unit_key'),
            'tax_object': concept.get('tax_object'),
            'tax_rate': tax_rate,
            'iva_exempt': bool(concept.get('iva_exempt')),
        })
    return payloads


def persist_xml_lines(invoice: dict, concepts: list[dict], user_id: int | None = None) -> list[dict]:
    return [
        InvoiceMaterialServiceService.create(payload, user_id=user_id)
        for payload in build_xml_line_payloads(invoice, concepts, user_id=user_id)
    ]
