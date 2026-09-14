"""Validacion del borrador CFDI 4.0 antes de enviarlo al PAC."""

from decimal import Decimal
from types import SimpleNamespace

from app.services.invoice_builder import (
    build_draft,
    draft_totals,
    inspect_draft,
    normalize_cfdi_type,
    normalize_cfdi_use,
    validate_draft,
)


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
        discount=Decimal("100"),
        tax_rate=Decimal("16"),
        isr_retention_rate=Decimal("10"),
        iva_retention_rate=Decimal("10.6667"),
        iva_exempt=False,
    )
    values.update(overrides)
    return _record(**values)


def _draft(payment_method="PUE", payment_form="03", lines=None, **invoice_overrides):
    invoice_values = dict(
        lugar_expedicion="37500",
        rfc_receptor="BBB010101BB1",
        nombre_receptor="CLIENTE DEMO SA DE CV",
        regimen_fiscal_receptor="601",
        domicilio_fiscal_receptor="37000",
        uso_cfdi="G03",
        forma_pago=payment_form,
        payment_method=payment_form,
        metodo_pago=payment_method,
        currency="MXN",
        type_exchange_rate=1,
        condiciones_pago="Contado",
        fiscal_certify_serie="A",
        serie_csd=None,
        folio="1",
        tipo_de_comprobante="I",
        exportacion="01",
    )
    invoice_values.update(invoice_overrides)
    invoice = _record(**invoice_values)
    issuer = _record(tax_id="AAA010101AA1", name="EMPRESA DEMO SA DE CV", fiscal_type="601", postal_code="37500")
    receiver = _record(
        tax_id=invoice_values["rfc_receptor"],
        name=invoice_values["nombre_receptor"],
        fiscal_type=invoice_values["regimen_fiscal_receptor"],
        postal_code="37000",
    )
    return build_draft(invoice, issuer, receiver, lines if lines is not None else [_line()])


def test_builds_valid_cfdi_draft_and_totals():
    draft = _draft()
    assert inspect_draft(draft) == {"errors": [], "warnings": []}
    assert draft_totals(draft) == {
        "subtotal": Decimal("1000.00"),
        "discount": Decimal("100.00"),
        "iva": Decimal("144.00"),
        "isr_retention": Decimal("90.00"),
        "iva_retention": Decimal("96.00"),
        "total": Decimal("858.00"),
    }


def test_totals_round_per_line_so_subtotal_matches_the_concepts():
    """El SAT exige SubTotal = suma de los Importe ya redondeados."""
    lines = [
        _line(quantity=3, gross_price=Decimal("33.333"), discount=Decimal("0"), tax_rate=Decimal("16"),
              isr_retention_rate=Decimal("0"), iva_retention_rate=Decimal("0")),
        _line(quantity=7, gross_price=Decimal("1.115"), discount=Decimal("0"), tax_rate=Decimal("16"),
              isr_retention_rate=Decimal("0"), iva_retention_rate=Decimal("0")),
    ]
    draft = _draft(lines=lines)
    totals = draft_totals(draft)

    assert [concept.amount for concept in draft.concepts] == [Decimal("100.00"), Decimal("7.81")]
    assert totals["subtotal"] == sum(concept.amount for concept in draft.concepts)
    assert totals["iva"] == sum(concept.transferred_iva for concept in draft.concepts)
    assert totals["total"] == totals["subtotal"] + totals["iva"]


def test_ppd_requires_payment_form_99_and_pue_forbids_it():
    assert "invoice.ppd_requires_payment_form_99" in validate_draft(_draft("PPD", "03"))
    assert "invoice.ppd_requires_payment_form_99" not in validate_draft(_draft("PPD", "99"))
    assert "invoice.pue_cannot_use_payment_form_99" in validate_draft(_draft("PUE", "99"))


def test_missing_or_malformed_sat_keys_block_stamping():
    draft = _draft()
    object.__setattr__(draft.concepts[0], "sat_product_key", "")
    assert "invoice.concepts.0.sat_product_key_required" in validate_draft(draft)

    draft = _draft(lines=[_line(sat_product_key="123")])
    assert "invoice.concepts.0.sat_product_key_invalid" in validate_draft(draft)

    draft = _draft(lines=[_line(sat_unit_key="PIEZAS")])
    assert "invoice.concepts.0.sat_unit_key_invalid" in validate_draft(draft)


def test_generic_receiver_must_use_publico_en_general_616_and_s01():
    errors = validate_draft(_draft(
        rfc_receptor="XAXX010101000",
        nombre_receptor="CLIENTE DEMO",
        regimen_fiscal_receptor="612",
        uso_cfdi="G03",
    ))
    assert "invoice.generic_receiver_name_must_be_publico_en_general" in errors
    assert "invoice.generic_receiver_tax_regime_must_be_616" in errors
    assert "invoice.generic_receiver_cfdi_use_must_be_s01" in errors

    assert validate_draft(_draft(
        rfc_receptor="XAXX010101000",
        nombre_receptor="PUBLICO EN GENERAL",
        regimen_fiscal_receptor="616",
        uso_cfdi="S01",
    )) == []


def test_foreign_receiver_requires_616_and_s01():
    errors = validate_draft(_draft(
        rfc_receptor="XEXX010101000",
        nombre_receptor="FOREIGN CUSTOMER LLC",
        regimen_fiscal_receptor="601",
        uso_cfdi="G03",
    ))
    assert "invoice.foreign_receiver_tax_regime_must_be_616" in errors
    assert "invoice.foreign_receiver_cfdi_use_must_be_s01" in errors


def test_tax_regime_must_exist_and_match_the_kind_of_person():
    assert "invoice.receiver_tax_regime_not_in_catalog" in validate_draft(
        _draft(regimen_fiscal_receptor="999")
    )
    # 601 es exclusivo de persona moral; el RFC de 13 posiciones es fisica.
    assert "invoice.receiver_tax_regime_person_mismatch" in validate_draft(
        _draft(rfc_receptor="BBBB010101BB1", regimen_fiscal_receptor="601")
    )


def test_cfdi_use_must_be_compatible_with_the_receiver_tax_regime():
    # D01 (honorarios medicos) no aplica al regimen 601 de persona moral.
    assert "invoice.cfdi_use_incompatible_with_receiver_tax_regime" in validate_draft(
        _draft(uso_cfdi="D01")
    )
    assert "invoice.cfdi_use_not_in_catalog" in validate_draft(_draft(uso_cfdi="ZZ99"))


def test_iva_rate_outside_the_sat_catalog_is_rejected():
    assert "invoice.concepts.0.iva_rate_not_in_catalog" in validate_draft(
        _draft(lines=[_line(tax_rate=Decimal("15"))])
    )
    for rate in ("0", "8", "16"):
        assert validate_draft(_draft(lines=[_line(
            tax_rate=Decimal(rate), isr_retention_rate=Decimal("0"), iva_retention_rate=Decimal("0")
        )])) == []


def test_tax_object_without_breakdown_cannot_carry_rates():
    # ObjetoImp 03 = si objeto pero sin desglose: no admite nodo Impuestos.
    draft = _draft(lines=[_line(tax_object="03")])
    assert "invoice.concepts.0.tax_object_forbids_tax_breakdown" in validate_draft(draft)

    clean = _draft(lines=[_line(
        tax_object="03", tax_rate=Decimal("0"), isr_retention_rate=Decimal("0"),
        iva_retention_rate=Decimal("0"),
    )])
    assert validate_draft(clean) == []
    # Sin desglose no se calcula ningun impuesto.
    assert draft_totals(clean)["iva"] == Decimal("0.00")
    assert draft_totals(clean)["total"] == Decimal("900.00")


def test_exempt_iva_is_not_the_same_as_zero_rate():
    exempt = _draft(lines=[_line(
        iva_exempt=True, tax_rate=Decimal("0"),
        isr_retention_rate=Decimal("0"), iva_retention_rate=Decimal("0"),
    )])
    assert validate_draft(exempt) == []
    assert exempt.concepts[0].transferred_iva == Decimal("0")

    contradictory = _draft(lines=[_line(
        iva_exempt=True, tax_rate=Decimal("16"),
        isr_retention_rate=Decimal("0"), iva_retention_rate=Decimal("0"),
    )])
    assert "invoice.concepts.0.exempt_iva_cannot_have_rate" in validate_draft(contradictory)


def test_currency_and_exchange_rate_rules():
    assert "invoice.exchange_rate_must_be_one_for_mxn" in validate_draft(
        _draft(currency="MXN", type_exchange_rate=17)
    )
    assert "invoice.exchange_rate_required_for_foreign_currency" in validate_draft(
        _draft(currency="USD", type_exchange_rate=0)
    )
    assert validate_draft(_draft(currency="USD", type_exchange_rate=Decimal("17.25"))) == []


def test_discount_cannot_exceed_the_line_amount():
    assert "invoice.concepts.0.discount_invalid" in validate_draft(
        _draft(lines=[_line(gross_price=Decimal("100"), discount=Decimal("200"))])
    )


def test_issuer_cannot_use_a_generic_rfc():
    invoice = _record(
        lugar_expedicion="37500", rfc_receptor="BBB010101BB1", nombre_receptor="CLIENTE",
        regimen_fiscal_receptor="601", domicilio_fiscal_receptor="37000", uso_cfdi="G03",
        forma_pago="03", payment_method="03", metodo_pago="PUE", currency="MXN",
        type_exchange_rate=1, condiciones_pago="", fiscal_certify_serie="A", serie_csd=None,
        folio="1", tipo_de_comprobante="I", exportacion="01",
    )
    issuer = _record(tax_id="XAXX010101000", name="EMISOR", fiscal_type="616", postal_code="37500")
    receiver = _record(tax_id="BBB010101BB1", name="CLIENTE", fiscal_type="601", postal_code="37000")
    errors = validate_draft(build_draft(invoice, issuer, receiver, [_line()]))
    assert "invoice.issuer_rfc_cannot_be_generic" in errors


def test_local_labels_are_translated_to_sat_codes():
    assert normalize_cfdi_type("factura") == "I"
    assert normalize_cfdi_type("") == "I"
    assert normalize_cfdi_type("E") == "E"
    assert normalize_cfdi_use("P01") == "G03"
    assert normalize_cfdi_use("") == "G03"
    assert normalize_cfdi_use("s01") == "S01"


def test_draft_serialization_carries_rounded_amounts_and_totals():
    payload = _draft().serialize()
    concept = payload["concepts"][0]

    assert concept["taxable_base"] == "900.00"
    assert concept["transferred_iva"] == "144.00"
    assert concept["retained_isr"] == "90.00"
    assert concept["retained_iva"] == "96.00"
    assert concept["breaks_down_taxes"] is True
    assert payload["totals"]["total"] == "858.00"
    assert payload["cfdi_type"] == "I"
