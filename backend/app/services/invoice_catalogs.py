"""Catalogos SAT (Anexo 20, CFDI 4.0) usados por facturacion.

Fuente unica de verdad para el frontend (selects) y para la validacion
previa al timbrado. Los catalogos que el SAT publica completos y acotados
(regimen fiscal, uso CFDI, forma y metodo de pago, objeto de impuesto,
tasas de IVA) se replican integros y se usan para validar. Los catalogos
masivos (ClaveProdServ, ClaveUnidad) no se replican: de esos solo se valida
el formato y se ofrece una lista curada de claves de uso frecuente.
"""

from __future__ import annotations

import re
from decimal import Decimal


# --- c_RegimenFiscal -------------------------------------------------------
# valor: (descripcion, aplica_persona_fisica, aplica_persona_moral)
REGIMEN_FISCAL_DETALLE = {
    "601": ("General de Ley Personas Morales", False, True),
    "603": ("Personas Morales con Fines no Lucrativos", False, True),
    "605": ("Sueldos y Salarios e Ingresos Asimilados a Salarios", True, False),
    "606": ("Arrendamiento", True, False),
    "607": ("Regimen de Enajenacion o Adquisicion de Bienes", True, False),
    "608": ("Demas ingresos", True, False),
    "610": ("Residentes en el Extranjero sin Establecimiento Permanente en Mexico", True, True),
    "611": ("Ingresos por Dividendos (socios y accionistas)", True, False),
    "612": ("Personas Fisicas con Actividades Empresariales y Profesionales", True, False),
    "614": ("Ingresos por intereses", True, False),
    "615": ("Regimen de los ingresos por obtencion de premios", True, False),
    "616": ("Sin obligaciones fiscales", True, True),
    "620": ("Sociedades Cooperativas de Produccion que optan por diferir sus ingresos", False, True),
    "621": ("Incorporacion Fiscal", True, False),
    "622": ("Actividades Agricolas, Ganaderas, Silvicolas y Pesqueras", False, True),
    "623": ("Opcional para Grupos de Sociedades", False, True),
    "624": ("Coordinados", False, True),
    "625": ("Actividades Empresariales con ingresos a traves de Plataformas Tecnologicas", True, False),
    "626": ("Regimen Simplificado de Confianza", True, True),
}
REGIMEN_FISCAL = {key: value[0] for key, value in REGIMEN_FISCAL_DETALLE.items()}

# Regimenes aplicables a persona moral (RFC de 12 posiciones) y a persona
# fisica (RFC de 13 posiciones).
REGIMEN_PERSONA_MORAL = {key for key, value in REGIMEN_FISCAL_DETALLE.items() if value[2]}
REGIMEN_PERSONA_FISICA = {key for key, value in REGIMEN_FISCAL_DETALLE.items() if value[1]}


# --- c_UsoCFDI -------------------------------------------------------------
_USO_EMPRESARIAL = {"601", "603", "606", "612", "620", "621", "622", "623", "624", "625", "626"}
_USO_DEDUCCION_PERSONAL = {"605", "606", "607", "608", "611", "612", "614", "615", "625"}
_TODOS_LOS_REGIMENES = set(REGIMEN_FISCAL_DETALLE)

USO_CFDI_DETALLE = {
    "G01": ("Adquisicion de mercancias", _USO_EMPRESARIAL),
    "G02": ("Devoluciones, descuentos o bonificaciones", _USO_EMPRESARIAL),
    "G03": ("Gastos en general", _USO_EMPRESARIAL),
    "I01": ("Construcciones", _USO_EMPRESARIAL),
    "I02": ("Mobiliario y equipo de oficina por inversiones", _USO_EMPRESARIAL),
    "I03": ("Equipo de transporte", _USO_EMPRESARIAL),
    "I04": ("Equipo de computo y accesorios", _USO_EMPRESARIAL),
    "I05": ("Dados, troqueles, moldes, matrices y herramental", _USO_EMPRESARIAL),
    "I06": ("Comunicaciones telefonicas", _USO_EMPRESARIAL),
    "I07": ("Comunicaciones satelitales", _USO_EMPRESARIAL),
    "I08": ("Otra maquinaria y equipo", _USO_EMPRESARIAL),
    "D01": ("Honorarios medicos, dentales y gastos hospitalarios", _USO_DEDUCCION_PERSONAL),
    "D02": ("Gastos medicos por incapacidad o discapacidad", _USO_DEDUCCION_PERSONAL),
    "D03": ("Gastos funerales", _USO_DEDUCCION_PERSONAL),
    "D04": ("Donativos", _USO_DEDUCCION_PERSONAL),
    "D05": ("Intereses reales por creditos hipotecarios de casa habitacion", _USO_DEDUCCION_PERSONAL),
    "D06": ("Aportaciones voluntarias al SAR", _USO_DEDUCCION_PERSONAL),
    "D07": ("Primas por seguros de gastos medicos", _USO_DEDUCCION_PERSONAL),
    "D08": ("Gastos de transportacion escolar obligatoria", _USO_DEDUCCION_PERSONAL),
    "D09": ("Depositos en cuentas para el ahorro y planes de pensiones", _USO_DEDUCCION_PERSONAL),
    "D10": ("Pagos por servicios educativos (colegiaturas)", _USO_DEDUCCION_PERSONAL),
    "S01": ("Sin efectos fiscales", _TODOS_LOS_REGIMENES),
    "CP01": ("Pagos", _TODOS_LOS_REGIMENES),
    "CN01": ("Nomina", {"605"}),
}
USO_CFDI = {key: value[0] for key, value in USO_CFDI_DETALLE.items()}
USO_REGIMENES_VALIDOS = {key: sorted(value[1]) for key, value in USO_CFDI_DETALLE.items()}


# --- c_FormaPago -----------------------------------------------------------
FORMA_PAGO = {
    "01": "Efectivo",
    "02": "Cheque nominativo",
    "03": "Transferencia electronica de fondos",
    "04": "Tarjeta de credito",
    "05": "Monedero electronico",
    "06": "Dinero electronico",
    "08": "Vales de despensa",
    "12": "Dacion en pago",
    "13": "Pago por subrogacion",
    "14": "Pago por consignacion",
    "15": "Condonacion",
    "17": "Compensacion",
    "23": "Novacion",
    "24": "Confusion",
    "25": "Remision de deuda",
    "26": "Prescripcion o caducidad",
    "27": "A satisfaccion del acreedor",
    "28": "Tarjeta de debito",
    "29": "Tarjeta de servicios",
    "30": "Aplicacion de anticipos",
    "31": "Intermediario pagos",
    "99": "Por definir",
}

METODO_PAGO = {
    "PUE": "Pago en una sola exhibicion",
    "PPD": "Pago en parcialidades o diferido",
}


# --- c_TipoDeComprobante / c_Exportacion ----------------------------------
TIPO_COMPROBANTE = {
    "I": "Ingreso",
    "E": "Egreso",
    "T": "Traslado",
    "N": "Nomina",
    "P": "Pago",
}

# --- c_TipoRelacion ---------------------------------------------------------
# Como se relaciona un comprobante con otro. Es lo que convierte un CFDI de
# egreso en una nota de credito de una factura concreta.
TIPO_RELACION = {
    "01": "Nota de credito de los documentos relacionados",
    "02": "Nota de debito de los documentos relacionados",
    "03": "Devolucion de mercancia sobre facturas o traslados previos",
    "04": "Sustitucion de los CFDI previos",
    "05": "Traslados de mercancias facturados previamente",
    "06": "Factura generada por los traslados previos",
    "07": "CFDI por aplicacion de anticipo",
}

# Relaciones con las que se emite una nota de credito. La 03 devuelve
# mercancia, asi que ademas mueve el almacen; la 01 es un descuento o
# bonificacion y no toca existencias.
TIPO_RELACION_NOTA_CREDITO = {"01", "03"}
TIPO_RELACION_DEVUELVE_MERCANCIA = "03"


EXPORTACION = {
    "01": "No aplica",
    "02": "Definitiva con clave A1",
    "03": "Temporal",
    "04": "Definitiva con clave distinta a A1 o cuando no existe enajenacion",
}


# --- c_ObjetoImp -----------------------------------------------------------
OBJETO_IMP = {
    "01": "No objeto de impuesto",
    "02": "Si objeto de impuesto",
    "03": "Si objeto del impuesto y no obligado al desglose",
    "04": "Si objeto del impuesto y no causa impuesto",
    "05": "Si objeto del impuesto, IVA credito PODEBI",
    "06": "Si objeto del impuesto, IVA no pagado PODEBI",
    "07": "Si objeto del impuesto, IVA y IEPS no pagado PODEBI",
    "08": "Si objeto del impuesto, no causa IVA por PODEBI",
}

# Objetos de impuesto que exigen el nodo Impuestos dentro del concepto.
OBJETO_IMP_CON_DESGLOSE = {"02", "05", "06", "07"}
# Objetos de impuesto que prohiben el nodo Impuestos dentro del concepto.
OBJETO_IMP_SIN_DESGLOSE = {"01", "03", "04", "08"}


# --- c_Impuesto y c_TasaOCuota --------------------------------------------
IMPUESTO = {"001": "ISR", "002": "IVA", "003": "IEPS"}

# Tasas de traslado de IVA permitidas por el SAT.
TASAS_IVA_TRASLADO = {Decimal("0.000000"), Decimal("0.080000"), Decimal("0.160000")}
# Tasas de retencion de IVA de uso habitual (arrendamiento, fletes, honorarios).
TASAS_IVA_RETENCION = {
    Decimal("0.040000"),
    Decimal("0.060000"),
    Decimal("0.080000"),
    Decimal("0.106667"),
    Decimal("0.160000"),
}
# Tasas de retencion de ISR de uso habitual (honorarios, arrendamiento, RESICO).
TASAS_ISR_RETENCION = {
    Decimal("0.012500"),
    Decimal("0.100000"),
    Decimal("0.200000"),
    Decimal("0.210000"),
}


# --- Catalogos masivos: solo formato + lista curada para captura ----------
CLAVE_PROD_SERV_PATTERN = re.compile(r"^[0-9]{8}$")
CLAVE_UNIDAD_PATTERN = re.compile(r"^[0-9A-Z]{1,3}$")

CLAVE_UNIDAD_FRECUENTES = {
    "H87": "Pieza",
    "EA": "Elemento",
    "E48": "Unidad de servicio",
    "ACT": "Actividad",
    "KGM": "Kilogramo",
    "GRM": "Gramo",
    "LTR": "Litro",
    "MLT": "Mililitro",
    "MTR": "Metro",
    "MTK": "Metro cuadrado",
    "MTQ": "Metro cubico",
    "CMT": "Centimetro",
    "HUR": "Hora",
    "DAY": "Dia",
    "MON": "Mes",
    "XBX": "Caja",
    "XPK": "Paquete",
    "SET": "Juego",
    "KT": "Kit",
    "E51": "Trabajo",
}

CLAVE_PROD_SERV_FRECUENTES = {
    "01010101": "No existe en el catalogo",
    "78102200": "Transporte de carga por carretera",
    "80101500": "Servicios de consultoria de negocios",
    "81111500": "Servicios de programacion y consultoria informatica",
    "84111500": "Servicios contables",
    "85121800": "Servicios medicos",
    "90101500": "Servicios de restaurante y comida",
    "43211500": "Computadoras",
    "44121600": "Articulos de papeleria",
    "50192700": "Alimentos preparados",
}

# RFC genericos definidos por el SAT.
RFC_PUBLICO_GENERAL = "XAXX010101000"
RFC_RESIDENTE_EXTRANJERO = "XEXX010101000"
NOMBRE_PUBLICO_GENERAL = "PUBLICO EN GENERAL"


def catalogs_payload():
    """Payload consumido por el frontend para poblar los selects de captura."""
    return {
        "regimen_fiscal": REGIMEN_FISCAL,
        "regimen_fiscal_persona_fisica": sorted(REGIMEN_PERSONA_FISICA),
        "regimen_fiscal_persona_moral": sorted(REGIMEN_PERSONA_MORAL),
        "uso_cfdi": USO_CFDI,
        "uso_regimenes_validos": USO_REGIMENES_VALIDOS,
        "forma_pago": FORMA_PAGO,
        "metodo_pago": METODO_PAGO,
        "tipo_comprobante": TIPO_COMPROBANTE,
        "tipo_relacion": TIPO_RELACION,
        "tipo_relacion_nota_credito": sorted(TIPO_RELACION_NOTA_CREDITO),
        "exportacion": EXPORTACION,
        "objeto_imp": OBJETO_IMP,
        "impuesto": IMPUESTO,
        "clave_unidad": CLAVE_UNIDAD_FRECUENTES,
        "clave_prod_serv": CLAVE_PROD_SERV_FRECUENTES,
        "tasas_iva_traslado": [format(rate, "f") for rate in sorted(TASAS_IVA_TRASLADO)],
        "tasas_iva_retencion": [format(rate, "f") for rate in sorted(TASAS_IVA_RETENCION)],
        "tasas_isr_retencion": [format(rate, "f") for rate in sorted(TASAS_ISR_RETENCION)],
        "rfc_genericos": {
            "publico_general": RFC_PUBLICO_GENERAL,
            "residente_extranjero": RFC_RESIDENTE_EXTRANJERO,
        },
    }
