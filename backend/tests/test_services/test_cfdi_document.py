"""El XML CFDI 4.0 que generamos debe pasar las reglas del Anexo 20."""

import xml.etree.ElementTree as ET
from decimal import Decimal
from types import SimpleNamespace

from app.services.cfdi_document import CFDI_NS, build_cfdi_xml
from app.services.cfdi_validation import inspect_cfdi_xml, validate_cfdi_xml
from app.services.invoice_artifacts import build_fake_cfdi_xml
from app.services.invoice_builder import build_draft


def _record(**values):
    return SimpleNamespace(**values)


def _line(**overrides):
    values = dict(
        quantity=1,
        gross_price=Decimal("1000"),
        invoice_material_service_description="Servicio de computo",
        sat_product_key="81111500",
        sat_unit_key="E48",
        tax_object="02",
        tax_applicable=True,
        discount=Decimal("0"),
        tax_rate=Decimal("16"),
        isr_retention_rate=Decimal("0"),
        iva_retention_rate=Decimal("0"),
        iva_exempt=False,
    )
    values.update(overrides)
    return _record(**values)


def _payload(lines=None, **invoice_overrides):
    invoice_values = dict(
        lugar_expedicion="37500", rfc_receptor="BBB010101BB1",
        nombre_receptor="CLIENTE DEMO SA DE CV", regimen_fiscal_receptor="601",
        domicilio_fiscal_receptor="37000", uso_cfdi="G03", forma_pago="03",
        payment_method="03", metodo_pago="PUE", currency="MXN", type_exchange_rate=1,
        condiciones_pago="Contado", fiscal_certify_serie="A", serie_csd=None, folio="7",
        tipo_de_comprobante="I", exportacion="01",
    )
    invoice_values.update(invoice_overrides)
    invoice = _record(**invoice_values)
    issuer = _record(tax_id="AAA010101AA1", name="EMPRESA DEMO SA DE CV", fiscal_type="601", postal_code="37500")
    receiver = _record(
        tax_id=invoice_values["rfc_receptor"], name=invoice_values["nombre_receptor"],
        fiscal_type=invoice_values["regimen_fiscal_receptor"], postal_code="37000",
    )
    return build_draft(invoice, issuer, receiver, lines if lines is not None else [_line()]).serialize()


def _element(xml, path):
    return ET.fromstring(xml).find(path.replace("cfdi:", "{%s}" % CFDI_NS))


def _elements(xml, path):
    return ET.fromstring(xml).findall(path.replace("cfdi:", "{%s}" % CFDI_NS))


def _attributes(xml):
    return ET.fromstring(xml).attrib


def test_stamped_document_passes_every_sat_rule():
    _, xml = build_fake_cfdi_xml(_payload())
    assert inspect_cfdi_xml(xml) == {"errors": [], "warnings": []}


def test_document_keeps_the_node_order_required_by_the_schema():
    _, xml = build_fake_cfdi_xml(_payload(lines=[_line(isr_retention_rate=Decimal("10"))]))
    children = [child.tag.split("}")[-1] for child in ET.fromstring(xml)]
    assert children == ["Emisor", "Receptor", "Conceptos", "Impuestos", "Complemento"]

    # En el concepto van Traslados y luego Retenciones.
    concept_taxes = _element(xml, "cfdi:Conceptos/cfdi:Concepto/cfdi:Impuestos")
    assert [child.tag.split("}")[-1] for child in concept_taxes] == ["Traslados", "Retenciones"]

    # A nivel comprobante el orden se invierte.
    summary = _element(xml, "cfdi:Impuestos")
    assert [child.tag.split("}")[-1] for child in summary] == ["Retenciones", "Traslados"]


def test_totals_match_the_concepts_even_with_decimal_unit_prices():
    lines = [
        _line(quantity=3, gross_price=Decimal("33.333")),
        _line(quantity=7, gross_price=Decimal("1.115")),
    ]
    payload = _payload(lines=lines)
    _, xml = build_fake_cfdi_xml(payload)

    attributes = _attributes(xml)
    concepts = _elements(xml, "cfdi:Conceptos/cfdi:Concepto")
    concept_amounts = sum(Decimal(item.attrib["Importe"]) for item in concepts)

    assert Decimal(attributes["SubTotal"]) == concept_amounts
    # El total guardado en la factura y el del XML deben ser el mismo numero.
    assert attributes["SubTotal"] == payload["totals"]["subtotal"]
    assert attributes["Total"] == payload["totals"]["total"]
    # ValorUnitario conserva los 6 decimales que permite el SAT.
    assert concepts[0].attrib["ValorUnitario"] == "33.333"
    assert validate_cfdi_xml(xml) == []


def test_discount_is_declared_both_per_concept_and_in_the_total():
    payload = _payload(lines=[_line(discount=Decimal("100"))])
    _, xml = build_fake_cfdi_xml(payload)

    concept = _element(xml, "cfdi:Conceptos/cfdi:Concepto")
    assert concept.attrib["Descuento"] == "100.00"
    assert _attributes(xml)["Descuento"] == "100.00"
    # La base gravable descuenta antes de aplicar el IVA.
    traslado = _element(xml, "cfdi:Conceptos/cfdi:Concepto/cfdi:Impuestos/cfdi:Traslados/cfdi:Traslado")
    assert traslado.attrib["Base"] == "900.00"
    assert traslado.attrib["Importe"] == "144.00"
    assert validate_cfdi_xml(xml) == []


def test_exempt_transfer_declares_base_without_rate_or_amount():
    payload = _payload(lines=[_line(iva_exempt=True, tax_rate=Decimal("0"))])
    _, xml = build_fake_cfdi_xml(payload)

    traslado = _element(xml, "cfdi:Conceptos/cfdi:Concepto/cfdi:Impuestos/cfdi:Traslados/cfdi:Traslado")
    assert traslado.attrib["TipoFactor"] == "Exento"
    assert traslado.attrib["Base"] == "1000.00"
    assert "TasaOCuota" not in traslado.attrib
    assert "Importe" not in traslado.attrib
    # Un comprobante solo con exentos no declara TotalImpuestosTrasladados.
    assert "TotalImpuestosTrasladados" not in _element(xml, "cfdi:Impuestos").attrib
    assert _attributes(xml)["Total"] == "1000.00"
    assert validate_cfdi_xml(xml) == []


def test_zero_rate_is_declared_as_tasa_not_as_exempt():
    payload = _payload(lines=[_line(tax_rate=Decimal("0"))])
    _, xml = build_fake_cfdi_xml(payload)

    traslado = _element(xml, "cfdi:Conceptos/cfdi:Concepto/cfdi:Impuestos/cfdi:Traslados/cfdi:Traslado")
    assert traslado.attrib["TipoFactor"] == "Tasa"
    assert traslado.attrib["TasaOCuota"] == "0.000000"
    assert traslado.attrib["Importe"] == "0.00"
    assert validate_cfdi_xml(xml) == []


def test_concepts_without_tax_object_omit_the_tax_nodes():
    payload = _payload(lines=[_line(tax_object="01", tax_applicable=False, tax_rate=Decimal("0"))])
    _, xml = build_fake_cfdi_xml(payload)

    assert _element(xml, "cfdi:Conceptos/cfdi:Concepto/cfdi:Impuestos") is None
    # Sin impuestos el nodo resumen tampoco debe existir.
    assert _element(xml, "cfdi:Impuestos") is None
    assert validate_cfdi_xml(xml) == []


def test_summary_groups_transfers_by_rate_and_retentions_by_tax():
    lines = [
        _line(gross_price=Decimal("1000"), tax_rate=Decimal("16"), isr_retention_rate=Decimal("10")),
        _line(gross_price=Decimal("500"), tax_rate=Decimal("16")),
        _line(gross_price=Decimal("200"), tax_rate=Decimal("8")),
    ]
    _, xml = build_fake_cfdi_xml(_payload(lines=lines))

    transfers = {
        item.attrib["TasaOCuota"]: item.attrib["Importe"]
        for item in _elements(xml, "cfdi:Impuestos/cfdi:Traslados/cfdi:Traslado")
    }
    assert transfers == {"0.160000": "240.00", "0.080000": "16.00"}
    summary = _element(xml, "cfdi:Impuestos").attrib
    assert summary["TotalImpuestosTrasladados"] == "256.00"
    assert summary["TotalImpuestosRetenidos"] == "100.00"
    assert validate_cfdi_xml(xml) == []


def test_foreign_currency_declares_the_exchange_rate():
    payload = _payload(currency="USD", type_exchange_rate=Decimal("17.2534"))
    _, xml = build_fake_cfdi_xml(payload)

    assert _attributes(xml)["TipoCambio"] == "17.253400"
    assert validate_cfdi_xml(xml) == []


def test_mxn_does_not_declare_an_exchange_rate():
    _, xml = build_fake_cfdi_xml(_payload())
    assert "TipoCambio" not in _attributes(xml)


def test_unstamped_document_is_reported_as_pending_not_invalid():
    payload = _payload()
    xml = build_cfdi_xml(payload, issued_at="2026-08-26T10:00:00", certificate_number="30001000000400000001", seal="AAAA")

    review = inspect_cfdi_xml(xml)
    assert review["errors"] == []
    assert "cfdi.sin_timbre_fiscal_digital" in review["warnings"]
