"""
Catalogos SAT minimos para CFDI 4.0, acotados a lo que un restaurante
realmente necesita (no son los catalogos completos del SAT, que tienen
miles de entradas).
"""

# Regimen fiscal del emisor/receptor (catalogo c_RegimenFiscal completo del SAT).
REGIMEN_FISCAL = {
    '601': 'General de Ley Personas Morales',
    '603': 'Personas Morales con Fines no Lucrativos',
    '605': 'Sueldos y Salarios e Ingresos Asimilados a Salarios',
    '606': 'Arrendamiento',
    '608': 'Demas ingresos',
    '612': 'Personas Fisicas con Actividades Empresariales y Profesionales',
    '616': 'Sin obligaciones fiscales',
    '621': 'Incorporacion Fiscal',
    '625': 'Regimen de las Actividades Empresariales con ingresos a traves de Plataformas Tecnologicas',
    '626': 'Regimen Simplificado de Confianza (RESICO)',
}

# Uso que el receptor le dara al CFDI (CFDI 4.0; P01 ya no existe).
USO_CFDI = {
    'G01': 'Adquisicion de mercancias',
    'G03': 'Gastos en general',
    'S01': 'Sin efectos fiscales',
}

# Forma de pago (como se paga) -- mismo catalogo que ya usa el cobro en caja
# (efectivo/tarjeta/transferencia/mixto), mapeado a la clave SAT.
FORMA_PAGO = {
    '01': 'Efectivo',
    '03': 'Transferencia electronica de fondos',
    '04': 'Tarjeta de credito',
    '28': 'Tarjeta de debito',
}

PAYMENT_METHOD_TO_FORMA_PAGO = {
    'efectivo': '01',
    'transferencia': '03',
    'tarjeta': '04',
    'mixto': '01',  # el mixto no tiene una sola clave SAT; se reporta como efectivo por la parte principal
}

# Metodo de pago (cuando se paga). Un restaurante siempre cobra de contado.
METODO_PAGO = {
    'PUE': 'Pago en una sola exhibicion',
}

# Motivo de cancelacion (catalogo c_MotivoCancelacion del SAT)
MOTIVO_CANCELACION = {
    '01': 'Comprobante emitido con errores con relacion',
    '02': 'Comprobante emitido con errores sin relacion',
    '03': 'No se llevo a cabo la operacion',
    '04': 'Operacion nominativa relacionada en la factura global',
}

# Clave de unidad del concepto.
CLAVE_UNIDAD = {
    'E48': 'Unidad de servicio',
    'H87': 'Pieza',
    'ACT': 'Actividad',
}

# Clave de producto/servicio (c_ClaveProdServ): solo las relevantes a un
# restaurante, no el catalogo completo del SAT (~52,000 entradas).
CLAVE_PROD_SERV = {
    '90101501': 'Servicios de restaurantes de comida completa',
    '90101502': 'Servicios de bar y restaurante',
    '90101601': 'Servicios de banquetes',
    '90111905': 'Servicios de bebidas',
}


def catalogs_payload():
    """Devuelve todos los catalogos en un dict, para el formulario de facturar."""
    return {
        'regimen_fiscal': REGIMEN_FISCAL,
        'uso_cfdi': USO_CFDI,
        'forma_pago': FORMA_PAGO,
        'metodo_pago': METODO_PAGO,
        'clave_unidad': CLAVE_UNIDAD,
        'clave_prod_serv': CLAVE_PROD_SERV,
        'motivo_cancelacion': MOTIVO_CANCELACION,
    }
