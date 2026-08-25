"""
Arma un InvoiceDraft (CFDI neutro) a partir de una o varias Order YA
PAGADAS del restaurante. A diferencia de un sistema de facturacion general
no hay cotizaciones aqui: se factura directamente lo que ya se cobro en
caja, con los mismos montos (nunca se inventa un total distinto al que el
comensal realmente pago).

La propina NO se incluye en el CFDI (practica estandar en restaurantes:
la propina es una entrega voluntaria, no la contraprestacion de un bien o
servicio) -- la factura solo cubre el consumo de alimentos/bebidas.
"""
from .base import Emisor, Receptor, Concepto, InvoiceDraft
from .catalogs import PAYMENT_METHOD_TO_FORMA_PAGO

DEFAULT_CLAVE_PROD_SERV = '90101501'  # Servicios de restaurantes de comida completa
DEFAULT_CLAVE_UNIDAD = 'E48'          # Unidad de servicio


def build_draft_from_sale(orders, company, receptor_data, serie, folio):
    """orders: lista de Order (SQLAlchemy, ya pagadas) que se facturan
    JUNTAS -- normalmente una sola orden, o varias si fue un cobro
    combinado de mesa. company: Company (emisor). receptor_data: dict con
    rfc/nombre/regimen_fiscal/cp_fiscal/uso_cfdi ya capturados en el
    formulario de facturar."""
    emisor = Emisor(
        rfc=company.rfc, nombre=company.razon_social,
        regimen_fiscal=company.regimen_fiscal, cp=company.cp,
    )
    receptor = Receptor(
        rfc=receptor_data['rfc'], nombre=receptor_data['nombre'],
        regimen_fiscal=receptor_data['regimen_fiscal'], cp_fiscal=receptor_data['cp_fiscal'],
        uso_cfdi=receptor_data.get('uso_cfdi', 'G03'),
    )

    conceptos = []
    subtotal_bruto = 0.0
    discount_total = 0.0
    tax_total = 0.0
    payment_method = None
    for order in orders:
        payment_method = payment_method or order.payment_method
        discount_total += float(order.discount_amount or 0)
        tax_total += float(order.tax_amount or 0)
        for item in order.items:
            if item.status == 'cancelado':
                continue
            qty = float(item.quantity or 0)
            price = float(item.unit_price or 0)
            importe = round(qty * price, 2)
            subtotal_bruto += importe
            conceptos.append(Concepto(
                descripcion=item.dish.title if item.dish else 'Consumo',
                cantidad=qty, valor_unitario=price, importe=importe,
                clave_prod_serv=DEFAULT_CLAVE_PROD_SERV, clave_unidad=DEFAULT_CLAVE_UNIDAD,
            ))

    if not conceptos:
        # No debería pasar (no se puede facturar una cuenta vacía), pero se
        # deja un concepto neutro en vez de mandar un CFDI sin conceptos.
        conceptos = [Concepto('Consumo', 1, 0, 0, DEFAULT_CLAVE_PROD_SERV, DEFAULT_CLAVE_UNIDAD)]

    subtotal_neto = round(subtotal_bruto - discount_total, 2)
    # El descuento aplicado en caja se reparte proporcionalmente entre los
    # conceptos (mismo criterio que ya usa _distribute() en visits.py para
    # repartir propina/IVA/descuento en un cobro combinado), para que la
    # suma de los conceptos coincida con lo que el comensal realmente pagó.
    discount_factor = (subtotal_neto / subtotal_bruto) if subtotal_bruto > 0 else 1.0
    iva_rate = round(tax_total / subtotal_neto, 4) if subtotal_neto > 0 and tax_total > 0 else 0.0
    for c in conceptos:
        if discount_factor != 1.0:
            c.importe = round(c.importe * discount_factor, 2)
            if c.cantidad:
                c.valor_unitario = round(c.importe / c.cantidad, 2)
        c.iva_rate = iva_rate

    forma_pago = PAYMENT_METHOD_TO_FORMA_PAGO.get(payment_method or 'efectivo', '01')

    return InvoiceDraft(
        emisor=emisor, receptor=receptor, conceptos=conceptos,
        forma_pago=forma_pago, metodo_pago='PUE',
        uso_cfdi=receptor.uso_cfdi, serie=serie, folio=str(folio),
    )


def build_draft_nota_credito(original_draft, uuid_original):
    """Arma el draft de una nota de credito (CFDI de Egreso) que refleja y
    relaciona una factura ya timbrada -- para devoluciones/cancelaciones
    parciales. Copia los mismos conceptos/receptor/emisor de la original."""
    return InvoiceDraft(
        emisor=original_draft.emisor, receptor=original_draft.receptor,
        conceptos=original_draft.conceptos, forma_pago=original_draft.forma_pago,
        metodo_pago=original_draft.metodo_pago, uso_cfdi=original_draft.uso_cfdi,
        cfdi_type='E', serie=original_draft.serie, folio=original_draft.folio,
        relacion_uuid=uuid_original,
    )


def draft_totals(draft):
    """El IVA se suma a partir del mismo monto YA REDONDEADO por concepto
    que invoices.py guarda en cada InvoiceItem.iva_amount (ver create_invoice/
    create_nota_credito) -- sumar primero y redondear una sola vez al final
    (como se hacia antes) puede dar un total distinto a la suma real de los
    conceptos ya persistidos, dejando una factura que no reconcilia contra
    sus propias lineas."""
    subtotal = round(sum(c.importe for c in draft.conceptos), 2)
    iva = round(sum(round(c.importe * c.iva_rate, 2) for c in draft.conceptos), 2)
    total = round(subtotal + iva, 2)
    return {'subtotal': subtotal, 'iva': iva, 'total': total}
