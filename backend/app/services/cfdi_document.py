"""Construccion del documento XML CFDI 4.0 a partir de un borrador.

Genera un comprobante con la estructura y el orden de nodos que exige el
esquema cfdv40.xsd del SAT, incluido el desglose de impuestos por concepto y
el resumen a nivel comprobante. Se usa para el proveedor de timbrado local
(pruebas y demo) y como referencia de lo que debe producir un PAC real.

Reglas del Anexo 20 que aqui se respetan y que suelen provocar rechazos:

* El orden de los hijos de `Comprobante` es Emisor, Receptor, Conceptos,
  Impuestos, Complemento.
* Dentro de `Concepto/Impuestos` van primero `Traslados` y luego
  `Retenciones`; en `Comprobante/Impuestos` el orden se invierte.
* `SubTotal` es la suma de los `Importe` de cada concepto y `Descuento` la
  suma de los `Descuento` de cada concepto (nunca un redondeo del total).
* Un traslado exento declara `Base` y `TipoFactor="Exento"` sin `TasaOCuota`
  ni `Importe`, y no suma a `TotalImpuestosTrasladados`.
* Si ningun concepto desglosa impuestos, el nodo `Impuestos` se omite.
* `TipoCambio` es obligatorio con moneda distinta de MXN y XXX.
* `CfdiRelacionados` va ANTES de `Emisor`, y agrupa por tipo de relacion: un
  comprobante declara un solo tipo por nodo, con todos los folios de ese tipo
  dentro. Es lo que convierte un egreso en la nota de credito de una factura
  concreta.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from decimal import Decimal, ROUND_HALF_UP


CFDI_NS = "http://www.sat.gob.mx/cfd/4"
TFD_NS = "http://www.sat.gob.mx/TimbreFiscalDigital"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"
SCHEMA_LOCATION = (
    "http://www.sat.gob.mx/cfd/4 "
    "http://www.sat.gob.mx/sitio_internet/cfd/4/cfdv40.xsd"
)

IVA = "002"
ISR = "001"

ET.register_namespace("cfdi", CFDI_NS)
ET.register_namespace("tfd", TFD_NS)
ET.register_namespace("xsi", XSI_NS)


def _decimal(value) -> Decimal:
    return Decimal(str(value if value not in (None, "") else 0))


def _money(value) -> str:
    return format(_decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), "f")


def _rate(value) -> str:
    return format(_decimal(value).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP), "f")


def _amount(value) -> str:
    """Cantidad o ValorUnitario: hasta 6 decimales, sin ceros sobrantes."""
    number = _decimal(value).normalize()
    if number == number.to_integral_value():
        number = number.quantize(Decimal("1"))
    text = format(number, "f")
    return text if "." not in text else text.rstrip("0").rstrip(".") or "0"


def _concept_taxes(concept: dict) -> dict:
    """Impuestos de un concepto, ya redondeados, listos para el XML."""
    if not concept.get("breaks_down_taxes"):
        return {"traslados": [], "retenciones": []}

    base = _decimal(concept.get("taxable_base"))
    traslados = []
    retenciones = []

    if concept.get("iva_exempt"):
        traslados.append({"impuesto": IVA, "tipo_factor": "Exento", "base": base})
    else:
        traslados.append({
            "impuesto": IVA,
            "tipo_factor": "Tasa",
            "base": base,
            "tasa": _decimal(concept.get("iva_rate")),
            "importe": _decimal(concept.get("transferred_iva")),
        })

    if _decimal(concept.get("isr_retention_rate")) > 0:
        retenciones.append({
            "impuesto": ISR,
            "tipo_factor": "Tasa",
            "base": base,
            "tasa": _decimal(concept.get("isr_retention_rate")),
            "importe": _decimal(concept.get("retained_isr")),
        })
    if _decimal(concept.get("iva_retention_rate")) > 0:
        retenciones.append({
            "impuesto": IVA,
            "tipo_factor": "Tasa",
            "base": base,
            "tasa": _decimal(concept.get("iva_retention_rate")),
            "importe": _decimal(concept.get("retained_iva")),
        })
    return {"traslados": traslados, "retenciones": retenciones}


def _append_tax_nodes(parent, tag_group, tag_item, entries) -> None:
    if not entries:
        return
    group = ET.SubElement(parent, f"{{{CFDI_NS}}}{tag_group}")
    for entry in entries:
        attributes = {"Base": _money(entry["base"]), "Impuesto": entry["impuesto"], "TipoFactor": entry["tipo_factor"]}
        if entry["tipo_factor"] != "Exento":
            attributes["TasaOCuota"] = _rate(entry["tasa"])
            attributes["Importe"] = _money(entry["importe"])
        ET.SubElement(group, f"{{{CFDI_NS}}}{tag_item}", attributes)


def _summary_taxes(all_taxes: list[dict]) -> dict:
    """Agrupa los impuestos de todos los conceptos como los pide el SAT.

    Los traslados se agrupan por (Impuesto, TipoFactor, TasaOCuota) y las
    retenciones por Impuesto, sumando los importes ya redondeados de cada
    concepto para que el resumen cuadre con el desglose.
    """
    traslados: dict[tuple, dict] = {}
    retenciones: dict[str, Decimal] = {}
    for taxes in all_taxes:
        for entry in taxes["traslados"]:
            key = (entry["impuesto"], entry["tipo_factor"], _rate(entry.get("tasa", 0)))
            group = traslados.setdefault(key, {"base": Decimal("0"), "importe": Decimal("0")})
            group["base"] += entry["base"]
            group["importe"] += entry.get("importe", Decimal("0"))
        for entry in taxes["retenciones"]:
            retenciones[entry["impuesto"]] = retenciones.get(entry["impuesto"], Decimal("0")) + entry["importe"]
    return {"traslados": traslados, "retenciones": retenciones}


def _append_summary(root, all_taxes: list[dict]) -> None:
    summary = _summary_taxes(all_taxes)
    if not summary["traslados"] and not summary["retenciones"]:
        return

    transferred_total = sum(
        (group["importe"] for key, group in summary["traslados"].items() if key[1] != "Exento"),
        Decimal("0"),
    )
    retained_total = sum(summary["retenciones"].values(), Decimal("0"))
    has_non_exempt_transfer = any(key[1] != "Exento" for key in summary["traslados"])

    attributes = {}
    if summary["retenciones"]:
        attributes["TotalImpuestosRetenidos"] = _money(retained_total)
    if has_non_exempt_transfer:
        attributes["TotalImpuestosTrasladados"] = _money(transferred_total)
    node = ET.SubElement(root, f"{{{CFDI_NS}}}Impuestos", attributes)

    # A nivel comprobante el XSD pide Retenciones antes de Traslados.
    if summary["retenciones"]:
        group = ET.SubElement(node, f"{{{CFDI_NS}}}Retenciones")
        for tax, amount in sorted(summary["retenciones"].items()):
            ET.SubElement(group, f"{{{CFDI_NS}}}Retencion", {"Impuesto": tax, "Importe": _money(amount)})
    if summary["traslados"]:
        group = ET.SubElement(node, f"{{{CFDI_NS}}}Traslados")
        for (tax, factor, rate), values in sorted(summary["traslados"].items()):
            transfer = {"Base": _money(values["base"]), "Impuesto": tax, "TipoFactor": factor}
            if factor != "Exento":
                transfer["TasaOCuota"] = rate
                transfer["Importe"] = _money(values["importe"])
            ET.SubElement(group, f"{{{CFDI_NS}}}Traslado", transfer)


def _append_related(root, related) -> None:
    """Comprobantes con los que este se relaciona.

    El SAT agrupa por tipo: un nodo por cada tipo de relacion, con los folios
    de ese tipo dentro. Va antes del emisor porque asi lo ordena el esquema.
    """
    if not related:
        return
    por_tipo: dict[str, list[str]] = {}
    for elemento in related:
        tipo = str(elemento.get("relation_type") or "").strip()
        uuid = str(elemento.get("uuid") or "").strip().upper()
        if not tipo or not uuid:
            continue
        if uuid not in por_tipo.setdefault(tipo, []):
            por_tipo[tipo].append(uuid)

    for tipo, folios in sorted(por_tipo.items()):
        nodo = ET.SubElement(root, f"{{{CFDI_NS}}}CfdiRelacionados", {"TipoRelacion": tipo})
        for folio in folios:
            ET.SubElement(nodo, f"{{{CFDI_NS}}}CfdiRelacionado", {"UUID": folio})


def build_cfdi_xml(payload: dict, *, issued_at: str, certificate_number: str, seal: str, stamp: dict | None = None) -> str:
    """Serializa un CFDI 4.0 a partir del payload de `InvoiceDraft.serialize()`."""
    concepts = payload.get("concepts") or []
    issuer = payload.get("issuer") or {}
    receiver = payload.get("receiver") or {}
    currency = str(payload.get("currency") or "MXN").upper()

    # Los totales se derivan de los conceptos, no se toman del payload: asi el
    # comprobante no puede contradecir su propio desglose.
    all_taxes = [_concept_taxes(concept) for concept in concepts]
    subtotal = sum((_decimal(item.get("amount")) for item in concepts), Decimal("0"))
    discount = sum((_decimal(item.get("discount")) for item in concepts), Decimal("0"))
    transferred = sum(
        (entry.get("importe", Decimal("0")) for taxes in all_taxes for entry in taxes["traslados"]),
        Decimal("0"),
    )
    retained = sum(
        (entry["importe"] for taxes in all_taxes for entry in taxes["retenciones"]),
        Decimal("0"),
    )
    total = subtotal - discount + transferred - retained

    attributes = {
        f"{{{XSI_NS}}}schemaLocation": SCHEMA_LOCATION,
        "Version": "4.0",
        "Fecha": issued_at,
        "Sello": seal,
        "NoCertificado": certificate_number,
        "Certificado": payload.get("certificate") or "MIIF" + certificate_number,
        "SubTotal": _money(subtotal),
        "Moneda": currency,
        "Total": _money(total),
        "TipoDeComprobante": str(payload.get("cfdi_type") or "I"),
        "Exportacion": str(payload.get("export_code") or "01"),
        "LugarExpedicion": str(issuer.get("postal_code") or ""),
    }
    if str(payload.get("payment_form") or ""):
        attributes["FormaPago"] = str(payload["payment_form"])
    if str(payload.get("payment_method") or ""):
        attributes["MetodoPago"] = str(payload["payment_method"])
    if discount > 0:
        attributes["Descuento"] = _money(discount)
    if currency not in {"MXN", "XXX"}:
        attributes["TipoCambio"] = _rate(payload.get("exchange_rate"))
    if payload.get("series"):
        attributes["Serie"] = str(payload["series"])
    if payload.get("folio"):
        attributes["Folio"] = str(payload["folio"])
    if payload.get("payment_conditions"):
        attributes["CondicionesDePago"] = str(payload["payment_conditions"])[:1000]

    root = ET.Element(f"{{{CFDI_NS}}}Comprobante", attributes)
    _append_related(root, payload.get("related_documents"))
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
        "UsoCFDI": str(receiver.get("cfdi_use") or ""),
    })

    concept_root = ET.SubElement(root, f"{{{CFDI_NS}}}Conceptos")
    for concept, taxes in zip(concepts, all_taxes):
        concept_attributes = {
            "ClaveProdServ": str(concept.get("sat_product_key") or ""),
            "Cantidad": _amount(concept.get("quantity")),
            "ClaveUnidad": str(concept.get("sat_unit_key") or ""),
            "Descripcion": str(concept.get("description") or ""),
            "ValorUnitario": _amount(concept.get("unit_price")),
            "Importe": _money(concept.get("amount")),
            "ObjetoImp": str(concept.get("tax_object") or "01"),
        }
        if _decimal(concept.get("discount")) > 0:
            concept_attributes["Descuento"] = _money(concept.get("discount"))
        node = ET.SubElement(concept_root, f"{{{CFDI_NS}}}Concepto", concept_attributes)

        if taxes["traslados"] or taxes["retenciones"]:
            tax_node = ET.SubElement(node, f"{{{CFDI_NS}}}Impuestos")
            _append_tax_nodes(tax_node, "Traslados", "Traslado", taxes["traslados"])
            _append_tax_nodes(tax_node, "Retenciones", "Retencion", taxes["retenciones"])

    _append_summary(root, all_taxes)

    if stamp:
        complement = ET.SubElement(root, f"{{{CFDI_NS}}}Complemento")
        ET.SubElement(complement, f"{{{TFD_NS}}}TimbreFiscalDigital", {
            f"{{{XSI_NS}}}schemaLocation": (
                "http://www.sat.gob.mx/TimbreFiscalDigital "
                "http://www.sat.gob.mx/sitio_internet/cfd/timbrefiscaldigital/TimbreFiscalDigitalv11.xsd"
            ),
            "Version": "1.1",
            "UUID": str(stamp["uuid"]),
            "FechaTimbrado": str(stamp["stamped_at"]),
            "RfcProvCertif": str(stamp["provider_rfc"]),
            "SelloCFD": str(stamp["cfd_seal"]),
            "NoCertificadoSAT": str(stamp["sat_certificate_number"]),
            "SelloSAT": str(stamp["sat_seal"]),
        })

    return ET.tostring(root, encoding="unicode", xml_declaration=True)
