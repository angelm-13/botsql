from __future__ import annotations

import os
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


CFDI_NS = "http://www.sat.gob.mx/cfd/4"
TFD_NS = "http://www.sat.gob.mx/TimbreFiscalDigital"
ET.register_namespace("cfdi", CFDI_NS)
ET.register_namespace("tfd", TFD_NS)


def _money(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def invoice_xml_path(invoice_id, upload_root=None) -> Path:
    root = Path(upload_root or os.getenv("UPLOAD_ROOT") or Path(__file__).resolve().parents[3] / "uploads")
    return root / "cfdi_xml" / f"invoice_{int(invoice_id)}.xml"


def save_invoice_xml(invoice_id, xml_content, upload_root=None) -> Path:
    content = xml_content.encode("utf-8") if isinstance(xml_content, str) else bytes(xml_content)
    path = invoice_xml_path(invoice_id, upload_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(".xml.tmp")
    temporary_path.write_bytes(content)
    temporary_path.replace(path)
    return path


def build_fake_cfdi_xml(payload: dict, stamp_uuid=None) -> tuple[str, str]:
    stamp_uuid = str(stamp_uuid or uuid.uuid4()).upper()
    concepts = payload.get("concepts") or []
    subtotal = sum((_money(item.get("amount")) for item in concepts), Decimal("0"))
    discount = sum((_money(item.get("discount")) for item in concepts), Decimal("0"))
    tax = sum(
        (_money((_money(item.get("amount")) - _money(item.get("discount"))) * Decimal(str(item.get("iva_rate") or 0))) for item in concepts),
        Decimal("0"),
    )
    retained = sum(
        (_money((_money(item.get("amount")) - _money(item.get("discount"))) * (Decimal(str(item.get("isr_retention_rate") or 0)) + Decimal(str(item.get("iva_retention_rate") or 0)))) for item in concepts),
        Decimal("0"),
    )
    total = subtotal - discount + tax - retained
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "")
    issuer = payload.get("issuer") or {}
    receiver = payload.get("receiver") or {}
    attributes = {
        "Version": "4.0",
        "Fecha": now,
        "SubTotal": format(subtotal, ".2f"),
        "Total": format(total, ".2f"),
        "Moneda": str(payload.get("currency") or "MXN"),
        "TipoDeComprobante": str(payload.get("cfdi_type") or "I"),
        "Exportacion": "01",
        "LugarExpedicion": str(issuer.get("postal_code") or ""),
        "FormaPago": str(payload.get("payment_form") or ""),
        "MetodoPago": str(payload.get("payment_method") or ""),
        "NoCertificado": "30001000000400000001",
    }
    if discount:
        attributes["Descuento"] = format(discount, ".2f")
    if payload.get("series"):
        attributes["Serie"] = str(payload["series"])
    if payload.get("folio"):
        attributes["Folio"] = str(payload["folio"])
    root = ET.Element(f"{{{CFDI_NS}}}Comprobante", attributes)
    ET.SubElement(root, f"{{{CFDI_NS}}}Emisor", {
        "Rfc": str(issuer.get("rfc") or ""),
        "Nombre": str(issuer.get("name") or ""),
        "RegimenFiscal": str(issuer.get("tax_regime") or ""),
    })
    ET.SubElement(root, f"{{{CFDI_NS}}}Receptor", {
        "Rfc": str(receiver.get("rfc") or ""),
        "Nombre": str(receiver.get("name") or ""),
        "DomicilioFiscalReceptor": str(receiver.get("postal_code") or ""),
        "RegimenFiscalReceptor": str(receiver.get("tax_regime") or ""),
        "UsoCFDI": str(receiver.get("cfdi_use") or "G03"),
    })
    concept_nodes = ET.SubElement(root, f"{{{CFDI_NS}}}Conceptos")
    for concept in concepts:
        ET.SubElement(concept_nodes, f"{{{CFDI_NS}}}Concepto", {
            "ClaveProdServ": str(concept.get("sat_product_key") or ""),
            "Cantidad": str(concept.get("quantity") or "0"),
            "ClaveUnidad": str(concept.get("sat_unit_key") or ""),
            "Descripcion": str(concept.get("description") or ""),
            "ValorUnitario": format(_money(concept.get("unit_price")), ".2f"),
            "Importe": format(_money(concept.get("amount")), ".2f"),
            "ObjetoImp": str(concept.get("tax_object") or "01"),
        })
    complement = ET.SubElement(root, f"{{{CFDI_NS}}}Complemento")
    ET.SubElement(complement, f"{{{TFD_NS}}}TimbreFiscalDigital", {
        "Version": "1.1",
        "UUID": stamp_uuid,
        "FechaTimbrado": now,
        "RfcProvCertif": "MOCK010101AAA",
        "SelloCFD": ("MOCKCFD" + stamp_uuid.replace("-", "")).ljust(128, "A"),
        "NoCertificadoSAT": "30001000000400000002",
        "SelloSAT": ("MOCKSAT" + stamp_uuid.replace("-", "")).ljust(128, "B"),
    })
    xml = ET.tostring(root, encoding="unicode", xml_declaration=True)
    return stamp_uuid, xml