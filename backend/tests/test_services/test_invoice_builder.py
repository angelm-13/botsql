from decimal import Decimal
from types import SimpleNamespace

from app.services.invoice_builder import build_draft, draft_totals, normalize_cfdi_use, validate_draft


def _record(**values):
    return SimpleNamespace(**values)


def _draft(payment_method="PUE", payment_form="03"):
    invoice = _record(
        lugar_expedicion="37500", rfc_receptor="XAXX010101000",
        nombre_receptor="CLIENTE DEMO", regimen_fiscal_receptor="612",
        domicilio_fiscal_receptor="37000", uso_cfdi="G03", forma_pago=payment_form,
        payment_method=payment_form, metodo_pago=payment_method, currency="MXN",
        type_exchange_rate=1, condiciones_pago="Contado", fiscal_certify_serie="A",
        serie_csd=None, folio="1",
    )
    issuer = _record(tax_id="XAX010101AAA", name="EMPRESA DEMO", fiscal_type="601", postal_code="37500")
    receiver = _record(tax_id="XAXX010101000", name="CLIENTE DEMO", fiscal_type="612", postal_code="37000")
    line = _record(
        quantity=1, gross_price=Decimal("1000"), invoice_material_service_description="Servicio de cómputo",
        sat_product_key="81111500", sat_unit_key="E48", tax_object="02", tax_applicable=True,
        discount=Decimal("100"), tax_rate=Decimal("16"), isr_retention_rate=Decimal("10"),
        iva_retention_rate=Decimal("10.6667"),
    )
    return build_draft(invoice, issuer, receiver, [line])


def test_builds_valid_cfdi_draft_and_totals():
    draft = _draft()
    assert validate_draft(draft) == []
    assert draft_totals(draft) == {
        "subtotal": Decimal("1000.00"), "discount": Decimal("100.00"),
        "iva": Decimal("144.00"), "isr_retention": Decimal("90.00"),
        "iva_retention": Decimal("96.00"), "total": Decimal("858.00"),
    }


def test_ppd_requires_payment_form_99():
    assert "invoice.ppd_requires_payment_form_99" in validate_draft(_draft("PPD", "03"))
    assert "invoice.ppd_requires_payment_form_99" not in validate_draft(_draft("PPD", "99"))


def test_missing_sat_key_blocks_stamping():
    draft = _draft()
    object.__setattr__(draft.concepts[0], "sat_product_key", "")
    assert "invoice.concepts.0.sat_product_key_required" in validate_draft(draft)


def test_legacy_cfdi_use_is_normalized():
    assert normalize_cfdi_use("P01") == "G03"