from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from decimal import Decimal, InvalidOperation


DEFAULT_MAX_XML_BYTES = 5 * 1024 * 1024
SUPPORTED_CFDI_VERSIONS = {"3.3", "4.0"}


def _attribute(element, *names):
    if element is None:
        return None
    attributes = {key.lower(): value for key, value in element.attrib.items()}
    for name in names:
        value = attributes.get(name.lower())
        if value is not None:
            return value
    return None


def _local_name(tag):
    return tag.split("}", 1)[-1] if "}" in tag else tag


def _first(root, name):
    return next((element for element in root.iter() if _local_name(element.tag) == name), None)


def _money(value, field):
    try:
        return Decimal(str(value or "0"))
    except InvalidOperation as exc:
        raise ValueError(f"CFDI con {field} invalido") from exc


def _concepts(root):
    concepts = []
    for element in root.iter():
        if _local_name(element.tag) != "Concepto":
            continue
        amount = _money(_attribute(element, "Importe"), "Importe de concepto")
        discount = _money(_attribute(element, "Descuento"), "Descuento de concepto")
        transferred_tax = Decimal("0")
        retained_tax = Decimal("0")
        tax_rate = None
        iva_exempt = False
        for tax in element.iter():
            tax_name = _local_name(tax.tag)
            tax_amount = _money(_attribute(tax, "Importe"), "Impuesto de concepto")
            if tax_name == "Traslado":
                transferred_tax += tax_amount
                if _attribute(tax, "Impuesto") == "002":
                    # El traslado exento no trae TasaOCuota ni Importe; hay que
                    # distinguirlo de la tasa 0% para no reemitirlo mal.
                    if _attribute(tax, "TipoFactor") == "Exento":
                        iva_exempt = True
                    else:
                        tax_rate = _attribute(tax, "TasaOCuota")
            elif tax_name == "Retencion":
                retained_tax += tax_amount
        concepts.append({
            "description": _attribute(element, "Descripcion") or "Sin descripcion",
            "quantity": format(_money(_attribute(element, "Cantidad"), "Cantidad de concepto"), "f"),
            "unit_price": format(_money(_attribute(element, "ValorUnitario"), "ValorUnitario de concepto"), "f"),
            "subtotal": format(amount, "f"),
            "discount": format(discount, "f"),
            "tax": format(transferred_tax, "f"),
            "retained_tax": format(retained_tax, "f"),
            "total": format(amount - discount + transferred_tax - retained_tax, "f"),
            "sat_product_key": _attribute(element, "ClaveProdServ") or "01010101",
            "sat_unit_key": _attribute(element, "ClaveUnidad"),
            "tax_object": _attribute(element, "ObjetoImp"),
            "tax_rate": tax_rate,
            "iva_exempt": iva_exempt,
        })
    return concepts


def _direct_child(root, name):
    """Hijo directo del comprobante.

    `_first` recorre el arbol completo y para `Impuestos` devolveria primero el
    nodo del concepto, no el resumen del comprobante.
    """
    return next((element for element in root if _local_name(element.tag) == name), None)


def _document_taxes(root, concepts):
    """Impuestos del comprobante: resumen si existe, si no la suma de conceptos.

    Calcularlos como Total - SubTotal era incorrecto en cuanto habia descuento
    o retenciones: en una factura de honorarios con retenciones el IVA
    trasladado salia en cero.
    """
    summary = _direct_child(root, "Impuestos")
    transferred = _attribute(summary, "TotalImpuestosTrasladados") if summary is not None else None
    retained = _attribute(summary, "TotalImpuestosRetenidos") if summary is not None else None
    if transferred is None and retained is None:
        transferred = format(sum((_money(item["tax"], "Impuesto") for item in concepts), Decimal("0")), "f")
        retained = format(sum((_money(item["retained_tax"], "Impuesto") for item in concepts), Decimal("0")), "f")
    cents = Decimal("0.01")
    return (
        _money(transferred, "TotalImpuestosTrasladados").quantize(cents),
        _money(retained, "TotalImpuestosRetenidos").quantize(cents),
    )


def parse_cfdi(xml_bytes, max_bytes=None):
    max_size = max_bytes or int(os.getenv("CFDI_XML_MAX_BYTES", DEFAULT_MAX_XML_BYTES))
    if not xml_bytes:
        raise ValueError("El archivo XML esta vacio")
    if len(xml_bytes) > max_size:
        raise ValueError(f"El archivo XML excede el limite de {max_size} bytes")

    lowered = xml_bytes[:8192].lower()
    if b"<!doctype" in lowered or b"<!entity" in lowered:
        raise ValueError("El XML contiene declaraciones DTD o entidades no permitidas")

    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        raise ValueError("El archivo no contiene XML valido") from exc

    if _local_name(root.tag) != "Comprobante":
        raise ValueError("El XML no es un comprobante CFDI")
    version = _attribute(root, "Version", "version")
    if version not in SUPPORTED_CFDI_VERSIONS:
        raise ValueError("Version CFDI no soportada; se requiere 3.3 o 4.0")

    emisor = _first(root, "Emisor")
    receptor = _first(root, "Receptor")
    timbre = _first(root, "TimbreFiscalDigital")
    uuid = str(_attribute(timbre, "UUID") or "").strip().upper()
    if not uuid:
        raise ValueError("El CFDI no contiene UUID de timbrado")

    subtotal = _money(_attribute(root, "SubTotal"), "SubTotal")
    total = _money(_attribute(root, "Total"), "Total")
    if subtotal < 0 or total < 0:
        raise ValueError("Los importes CFDI no pueden ser negativos")

    concepts = _concepts(root)
    transferred_tax, retained_tax = _document_taxes(root, concepts)
    return {
        "version": version,
        "subtotal": format(subtotal, "f"),
        "total": format(total, "f"),
        "tax": format(transferred_tax, "f"),
        "retained_tax": format(retained_tax, "f"),
        "descuento": _attribute(root, "Descuento"),
        "currency": _attribute(root, "Moneda") or "MXN",
        "type_exchange_rate": _attribute(root, "TipoCambio"),
        "payment_method": _attribute(root, "FormaPago"),
        "metodo_pago": _attribute(root, "MetodoPago"),
        "lugar_expedicion": _attribute(root, "LugarExpedicion"),
        "tipo_de_comprobante": _attribute(root, "TipoDeComprobante"),
        "exportacion": _attribute(root, "Exportacion"),
        "folio": _attribute(root, "Folio"),
        "no_certificado": _attribute(root, "NoCertificado"),
        "condiciones_pago": _attribute(root, "CondicionesDePago"),
        "fecha": _attribute(root, "Fecha"),
        "rfc_emisor": _attribute(emisor, "Rfc"),
        "nombre_emisor": _attribute(emisor, "Nombre"),
        "rfc_receptor": _attribute(receptor, "Rfc"),
        "nombre_receptor": _attribute(receptor, "Nombre"),
        "regimen_fiscal_receptor": _attribute(receptor, "RegimenFiscalReceptor"),
        "domicilio_fiscal_receptor": _attribute(receptor, "DomicilioFiscalReceptor"),
        "uuid": uuid,
        "no_certificado_sat": _attribute(timbre, "NoCertificadoSAT"),
        "sello_sat": _attribute(timbre, "SelloSAT"),
        "rfc_proveedor_certificacion": _attribute(timbre, "RfcProvCertif"),
        "certification_date": _attribute(timbre, "FechaTimbrado"),
        "conceptos": concepts,
    }
