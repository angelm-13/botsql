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

    return {
        "version": version,
        "subtotal": format(subtotal, "f"),
        "total": format(total, "f"),
        "tax": format(max(total - subtotal, Decimal("0")), "f"),
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
    }