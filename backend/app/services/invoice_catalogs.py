REGIMEN_FISCAL = {
    "601": "General de Ley Personas Morales", "603": "Personas Morales con Fines no Lucrativos",
    "605": "Sueldos y Salarios", "606": "Arrendamiento", "612": "Personas Físicas con Actividades Empresariales y Profesionales",
    "616": "Sin obligaciones fiscales", "621": "Incorporación Fiscal", "625": "Plataformas Tecnológicas",
    "626": "Régimen Simplificado de Confianza (RESICO)",
}
USO_CFDI = {
    "G01": "Adquisición de mercancías", "G02": "Devoluciones, descuentos o bonificaciones",
    "G03": "Gastos en general", "I01": "Construcciones", "CP01": "Pagos", "S01": "Sin efectos fiscales",
}
FORMA_PAGO = {
    "01": "Efectivo", "02": "Cheque nominativo", "03": "Transferencia electrónica de fondos",
    "04": "Tarjeta de crédito", "28": "Tarjeta de débito", "99": "Por definir",
}
METODO_PAGO = {"PUE": "Pago en una sola exhibición", "PPD": "Pago en parcialidades o diferido"}
CLAVE_UNIDAD = {
    "H87": "Pieza", "E48": "Unidad de servicio", "ACT": "Actividad", "KGM": "Kilogramo",
    "MTR": "Metro", "MTK": "Metro cuadrado", "HUR": "Hora",
}
OBJETO_IMP = {"01": "No objeto de impuesto", "02": "Sí objeto de impuesto", "03": "Sí objeto sin desglose"}
USO_REGIMENES_VALIDOS = {
    uso: sorted(REGIMEN_FISCAL) for uso in USO_CFDI
}


def catalogs_payload():
    return {
        "regimen_fiscal": REGIMEN_FISCAL, "uso_cfdi": USO_CFDI, "forma_pago": FORMA_PAGO,
        "metodo_pago": METODO_PAGO, "clave_unidad": CLAVE_UNIDAD, "objeto_imp": OBJETO_IMP,
        "clave_prod_serv": {"01010101": "No existe en el catálogo (genérico)"},
        "uso_regimenes_validos": USO_REGIMENES_VALIDOS,
    }