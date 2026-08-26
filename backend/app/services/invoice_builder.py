"""Armado y validacion del borrador de CFDI 4.0 previo al timbrado.

`build_draft` normaliza los datos de la factura y sus partidas, `draft_totals`
calcula los importes con las reglas de redondeo del Anexo 20 (se redondea por
partida y luego se suma, nunca al revés) y `inspect_draft` aplica las reglas de
validacion del SAT que hacen que un PAC rechace el comprobante.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from decimal import Decimal, ROUND_HALF_UP

from app.services.invoice_catalogs import (
    CLAVE_PROD_SERV_PATTERN,
    CLAVE_UNIDAD_PATTERN,
    EXPORTACION,
    FORMA_PAGO,
    METODO_PAGO,
    NOMBRE_PUBLICO_GENERAL,
    OBJETO_IMP,
    OBJETO_IMP_CON_DESGLOSE,
    OBJETO_IMP_SIN_DESGLOSE,
    REGIMEN_FISCAL,
    REGIMEN_PERSONA_FISICA,
    REGIMEN_PERSONA_MORAL,
    RFC_PUBLICO_GENERAL,
    RFC_RESIDENTE_EXTRANJERO,
    TASAS_ISR_RETENCION,
    TASAS_IVA_RETENCION,
    TASAS_IVA_TRASLADO,
    TIPO_COMPROBANTE,
    USO_CFDI_DETALLE,
)


MONEY = Decimal("0.01")
RATE = Decimal("0.000001")
RFC_PATTERN = re.compile(r"^[A-ZÑ&]{3,4}[0-9]{6}[A-Z0-9]{3}$")
CP_PATTERN = re.compile(r"^[0-9]{5}$")
VALID_PAYMENT_METHODS = set(METODO_PAGO)
VALID_PAYMENT_FORMS = set(FORMA_PAGO)

# Monedas sin decimales; el resto se maneja a dos posiciones.
CURRENCY_PATTERN = re.compile(r"^[A-Z]{3}$")


def _decimal(value) -> Decimal:
    return Decimal(str(value or 0))


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)


def _rate(value: Decimal) -> Decimal:
    return value.quantize(RATE, rounding=ROUND_HALF_UP)


def _as_rate(value) -> Decimal:
    """Acepta la tasa como fraccion (0.16) o como porcentaje (16)."""
    parsed = _decimal(value)
    return _rate(parsed / Decimal("100") if parsed > 1 else parsed)


def normalize_cfdi_use(value) -> str:
    normalized = str(value or "").strip().upper()
    return "G03" if not normalized or normalized == "P01" else normalized


@dataclass(frozen=True)
class Issuer:
    rfc: str
    name: str
    tax_regime: str
    postal_code: str


@dataclass(frozen=True)
class Receiver:
    rfc: str
    name: str
    tax_regime: str
    postal_code: str
    cfdi_use: str


@dataclass(frozen=True)
class InvoiceConcept:
    description: str
    quantity: Decimal
    unit_price: Decimal
    amount: Decimal
    sat_product_key: str
    sat_unit_key: str
    tax_object: str
    discount: Decimal = Decimal("0")
    iva_rate: Decimal = Decimal("0")
    isr_retention_rate: Decimal = Decimal("0")
    iva_retention_rate: Decimal = Decimal("0")
    iva_exempt: bool = False

    @property
    def taxable_base(self) -> Decimal:
        return self.amount - self.discount

    @property
    def breaks_down_taxes(self) -> bool:
        """Solo los ObjetoImp con desglose llevan nodo Impuestos."""
        return self.tax_object in OBJETO_IMP_CON_DESGLOSE

    @property
    def transferred_iva(self) -> Decimal:
        # El traslado exento no lleva Importe: solo declara la base.
        if not self.breaks_down_taxes or self.iva_exempt:
            return Decimal("0")
        return _money(self.taxable_base * self.iva_rate)

    @property
    def retained_isr(self) -> Decimal:
        if not self.breaks_down_taxes:
            return Decimal("0")
        return _money(self.taxable_base * self.isr_retention_rate)

    @property
    def retained_iva(self) -> Decimal:
        if not self.breaks_down_taxes:
            return Decimal("0")
        return _money(self.taxable_base * self.iva_retention_rate)

    @property
    def total(self) -> Decimal:
        return self.taxable_base + self.transferred_iva - self.retained_isr - self.retained_iva


@dataclass(frozen=True)
class InvoiceDraft:
    issuer: Issuer
    receiver: Receiver
    concepts: list[InvoiceConcept] = field(default_factory=list)
    payment_form: str = ""
    payment_method: str = ""
    currency: str = "MXN"
    exchange_rate: Decimal = Decimal("1")
    payment_conditions: str = ""
    series: str = ""
    folio: str = ""
    cfdi_type: str = "I"
    export_code: str = "01"

    def serialize(self) -> dict:
        def convert(value):
            if isinstance(value, Decimal):
                return format(value, "f")
            if isinstance(value, list):
                return [convert(item) for item in value]
            if isinstance(value, dict):
                return {key: convert(item) for key, item in value.items()}
            return value

        payload = convert(asdict(self))
        # Los importes derivados viajan al PAC ya redondeados para que el XML
        # timbrado cuadre exactamente con los totales que guardamos.
        for concept, source in zip(payload["concepts"], self.concepts):
            concept["taxable_base"] = format(source.taxable_base, "f")
            concept["transferred_iva"] = format(source.transferred_iva, "f")
            concept["retained_isr"] = format(source.retained_isr, "f")
            concept["retained_iva"] = format(source.retained_iva, "f")
            concept["total"] = format(source.total, "f")
            concept["breaks_down_taxes"] = source.breaks_down_taxes
        payload["totals"] = {key: format(value, "f") for key, value in draft_totals(self).items()}
        return payload


def normalize_cfdi_type(value) -> str:
    """Traduce etiquetas locales al codigo c_TipoDeComprobante."""
    normalized = str(value or "").strip().upper()
    aliases = {
        "FACTURA": "I",
        "INGRESO": "I",
        "EGRESO": "E",
        "NOTA DE CREDITO": "E",
        "TRASLADO": "T",
        "NOMINA": "N",
        "PAGO": "P",
        "": "I",
    }
    return aliases.get(normalized, normalized)


def build_draft(invoice, issuer, receiver, lines) -> InvoiceDraft:
    concepts = []
    for line in lines:
        quantity = _decimal(line.quantity)
        unit_price = _decimal(line.gross_price)
        concepts.append(
            InvoiceConcept(
                description=str(line.invoice_material_service_description or "").strip(),
                quantity=quantity,
                unit_price=unit_price,
                amount=_money(quantity * unit_price),
                sat_product_key=str(line.sat_product_key or "").strip(),
                sat_unit_key=str(line.sat_unit_key or "").strip().upper(),
                tax_object=str(line.tax_object or ("02" if line.tax_applicable else "01")),
                discount=_money(_decimal(line.discount)),
                iva_rate=_as_rate(line.tax_rate),
                isr_retention_rate=_as_rate(line.isr_retention_rate),
                iva_retention_rate=_as_rate(line.iva_retention_rate),
                iva_exempt=bool(getattr(line, "iva_exempt", False)),
            )
        )

    return InvoiceDraft(
        issuer=Issuer(
            rfc=str(issuer.tax_id or "").strip().upper(),
            name=str(issuer.name or "").strip(),
            tax_regime=str(issuer.fiscal_type or "").strip(),
            postal_code=str(invoice.lugar_expedicion or issuer.postal_code or "").strip(),
        ),
        receiver=Receiver(
            rfc=str(invoice.rfc_receptor or receiver.tax_id or "").strip().upper(),
            name=str(invoice.nombre_receptor or receiver.name or "").strip(),
            tax_regime=str(invoice.regimen_fiscal_receptor or receiver.fiscal_type or "").strip(),
            postal_code=str(invoice.domicilio_fiscal_receptor or receiver.postal_code or "").strip(),
            cfdi_use=normalize_cfdi_use(invoice.uso_cfdi),
        ),
        concepts=concepts,
        payment_form=str(invoice.forma_pago or invoice.payment_method or "").strip(),
        payment_method=str(invoice.metodo_pago or "").strip().upper(),
        currency=str(invoice.currency or "MXN").strip().upper(),
        # No se rellena con 1: un CFDI en moneda extranjera sin TipoCambio
        # debe fallar la validacion, no quedarse con un tipo de cambio falso.
        exchange_rate=_decimal(invoice.type_exchange_rate),
        payment_conditions=str(invoice.condiciones_pago or "").strip(),
        series=str(invoice.fiscal_certify_serie or invoice.serie_csd or "").strip(),
        folio=str(invoice.folio or "").strip(),
        cfdi_type=normalize_cfdi_type(getattr(invoice, "tipo_de_comprobante", None)),
        export_code=str(getattr(invoice, "exportacion", None) or "01").strip(),
    )


def draft_totals(draft: InvoiceDraft) -> dict[str, Decimal]:
    """Totales con redondeo por partida, como los valida el SAT.

    El Anexo 20 exige SubTotal = suma de los Importe de cada concepto y los
    impuestos totales = suma de los impuestos de cada concepto. Sumar sin
    redondear y redondear al final produce diferencias de centavos que el PAC
    rechaza (CFDI40129 / CFDI40144).
    """
    subtotal = sum((concept.amount for concept in draft.concepts), Decimal("0"))
    discount = sum((concept.discount for concept in draft.concepts), Decimal("0"))
    iva = sum((concept.transferred_iva for concept in draft.concepts), Decimal("0"))
    isr_retention = sum((concept.retained_isr for concept in draft.concepts), Decimal("0"))
    iva_retention = sum((concept.retained_iva for concept in draft.concepts), Decimal("0"))
    return {
        "subtotal": _money(subtotal),
        "discount": _money(discount),
        "iva": _money(iva),
        "isr_retention": _money(isr_retention),
        "iva_retention": _money(iva_retention),
        "total": _money(subtotal - discount + iva - isr_retention - iva_retention),
    }


def _regimes_for_rfc(rfc: str) -> set[str]:
    """Regimenes aplicables segun el tipo de persona que denota el RFC."""
    if len(rfc) == 12:
        return REGIMEN_PERSONA_MORAL
    if len(rfc) == 13:
        return REGIMEN_PERSONA_FISICA
    return set(REGIMEN_FISCAL)


def _validate_issuer(draft: InvoiceDraft, errors: list[str], warnings: list[str]) -> None:
    if not RFC_PATTERN.match(draft.issuer.rfc):
        errors.append("invoice.issuer_rfc_invalid")
    if not draft.issuer.name:
        errors.append("invoice.issuer_name_required")
    if not draft.issuer.tax_regime:
        errors.append("invoice.issuer_tax_regime_required")
    elif draft.issuer.tax_regime not in REGIMEN_FISCAL:
        errors.append("invoice.issuer_tax_regime_not_in_catalog")
    elif draft.issuer.tax_regime not in _regimes_for_rfc(draft.issuer.rfc):
        errors.append("invoice.issuer_tax_regime_person_mismatch")
    if not CP_PATTERN.match(draft.issuer.postal_code):
        errors.append("invoice.issuer_postal_code_invalid")
    if draft.issuer.rfc in {RFC_PUBLICO_GENERAL, RFC_RESIDENTE_EXTRANJERO}:
        errors.append("invoice.issuer_rfc_cannot_be_generic")


def _validate_receiver(draft: InvoiceDraft, errors: list[str], warnings: list[str]) -> None:
    receiver = draft.receiver
    if not RFC_PATTERN.match(receiver.rfc):
        errors.append("invoice.receiver_rfc_invalid")
    if not receiver.name:
        errors.append("invoice.receiver_name_required")
    if not receiver.cfdi_use:
        errors.append("invoice.cfdi_use_required")
    elif receiver.cfdi_use not in USO_CFDI_DETALLE:
        errors.append("invoice.cfdi_use_not_in_catalog")

    if not receiver.tax_regime:
        errors.append("invoice.receiver_tax_regime_required")
    elif receiver.tax_regime not in REGIMEN_FISCAL:
        errors.append("invoice.receiver_tax_regime_not_in_catalog")

    # RFC generico nacional: el SAT fija nombre, regimen y uso.
    if receiver.rfc == RFC_PUBLICO_GENERAL:
        if receiver.name.upper() != NOMBRE_PUBLICO_GENERAL:
            errors.append("invoice.generic_receiver_name_must_be_publico_en_general")
        if receiver.tax_regime != "616":
            errors.append("invoice.generic_receiver_tax_regime_must_be_616")
        if receiver.cfdi_use != "S01":
            errors.append("invoice.generic_receiver_cfdi_use_must_be_s01")
    elif receiver.rfc == RFC_RESIDENTE_EXTRANJERO:
        if receiver.tax_regime != "616":
            errors.append("invoice.foreign_receiver_tax_regime_must_be_616")
        if receiver.cfdi_use != "S01":
            errors.append("invoice.foreign_receiver_cfdi_use_must_be_s01")
        if draft.export_code == "01":
            warnings.append("invoice.foreign_receiver_export_code_review")
    else:
        if receiver.tax_regime in REGIMEN_FISCAL and receiver.tax_regime not in _regimes_for_rfc(receiver.rfc):
            errors.append("invoice.receiver_tax_regime_person_mismatch")
        allowed_regimes = USO_CFDI_DETALLE.get(receiver.cfdi_use, (None, set()))[1]
        if receiver.tax_regime in REGIMEN_FISCAL and allowed_regimes and receiver.tax_regime not in allowed_regimes:
            errors.append("invoice.cfdi_use_incompatible_with_receiver_tax_regime")

    # El domicilio fiscal del receptor es obligatorio en CFDI 4.0, incluso
    # para el publico en general (ahi se usa el CP del lugar de expedicion).
    if not CP_PATTERN.match(receiver.postal_code):
        errors.append("invoice.receiver_postal_code_invalid")


def _validate_header(draft: InvoiceDraft, errors: list[str], warnings: list[str]) -> None:
    if draft.cfdi_type not in TIPO_COMPROBANTE:
        errors.append("invoice.cfdi_type_invalid")
    if draft.export_code not in EXPORTACION:
        errors.append("invoice.export_code_invalid")
    if draft.payment_form not in VALID_PAYMENT_FORMS:
        errors.append("invoice.payment_form_invalid")
    if draft.payment_method not in VALID_PAYMENT_METHODS:
        errors.append("invoice.payment_method_invalid")
    if draft.payment_method == "PPD" and draft.payment_form != "99":
        errors.append("invoice.ppd_requires_payment_form_99")
    if draft.payment_method == "PUE" and draft.payment_form == "99":
        errors.append("invoice.pue_cannot_use_payment_form_99")

    if not CURRENCY_PATTERN.match(draft.currency):
        errors.append("invoice.currency_invalid")
    # Un tipo de cambio en cero significa "no capturado".
    if draft.currency == "MXN":
        if draft.exchange_rate not in (Decimal("0"), Decimal("1")):
            errors.append("invoice.exchange_rate_must_be_one_for_mxn")
    elif draft.currency == "XXX":
        if draft.exchange_rate not in (Decimal("0"), Decimal("1")):
            errors.append("invoice.exchange_rate_not_applicable_for_xxx")
    elif draft.exchange_rate <= 0:
        errors.append("invoice.exchange_rate_required_for_foreign_currency")
    elif draft.exchange_rate == Decimal("1"):
        warnings.append("invoice.exchange_rate_one_for_foreign_currency")

    if len(draft.payment_conditions) > 1000:
        errors.append("invoice.payment_conditions_too_long")


def _validate_concepts(draft: InvoiceDraft, errors: list[str], warnings: list[str]) -> None:
    if not draft.concepts:
        errors.append("invoice.concepts_required")

    for index, concept in enumerate(draft.concepts):
        prefix = f"invoice.concepts.{index}"
        if not concept.description:
            errors.append(f"{prefix}.description_required")
        elif len(concept.description) > 1000:
            errors.append(f"{prefix}.description_too_long")
        if concept.quantity <= 0:
            errors.append(f"{prefix}.quantity_invalid")
        if concept.unit_price < 0:
            errors.append(f"{prefix}.unit_price_invalid")
        if not concept.sat_product_key:
            errors.append(f"{prefix}.sat_product_key_required")
        elif not CLAVE_PROD_SERV_PATTERN.match(concept.sat_product_key):
            errors.append(f"{prefix}.sat_product_key_invalid")
        if not concept.sat_unit_key:
            errors.append(f"{prefix}.sat_unit_key_required")
        elif not CLAVE_UNIDAD_PATTERN.match(concept.sat_unit_key):
            errors.append(f"{prefix}.sat_unit_key_invalid")
        if concept.discount < 0 or concept.discount > concept.amount:
            errors.append(f"{prefix}.discount_invalid")

        if concept.tax_object not in OBJETO_IMP:
            errors.append(f"{prefix}.tax_object_invalid")
            continue

        has_rates = concept.iva_exempt or any(
            rate > 0
            for rate in (concept.iva_rate, concept.isr_retention_rate, concept.iva_retention_rate)
        )
        if concept.tax_object in OBJETO_IMP_SIN_DESGLOSE and has_rates:
            # ObjetoImp 01/03/04/08 no admite nodo Impuestos: si llegan tasas,
            # el total del concepto y el del comprobante no cuadrarian.
            errors.append(f"{prefix}.tax_object_forbids_tax_breakdown")

        if concept.tax_object in OBJETO_IMP_CON_DESGLOSE:
            if concept.iva_exempt and concept.iva_rate != 0:
                errors.append(f"{prefix}.exempt_iva_cannot_have_rate")
            elif not concept.iva_exempt and concept.iva_rate not in TASAS_IVA_TRASLADO:
                errors.append(f"{prefix}.iva_rate_not_in_catalog")
            if concept.isr_retention_rate > 0 and concept.isr_retention_rate not in TASAS_ISR_RETENCION:
                warnings.append(f"{prefix}.isr_retention_rate_unusual")
            if concept.iva_retention_rate > 0 and concept.iva_retention_rate not in TASAS_IVA_RETENCION:
                warnings.append(f"{prefix}.iva_retention_rate_unusual")
            if concept.retained_isr + concept.retained_iva > concept.taxable_base + concept.transferred_iva:
                errors.append(f"{prefix}.retentions_exceed_amount")


def _validate_totals(draft: InvoiceDraft, errors: list[str], warnings: list[str]) -> None:
    totals = draft_totals(draft)
    if totals["subtotal"] != _money(sum((c.amount for c in draft.concepts), Decimal("0"))):
        errors.append("invoice.subtotal_mismatch")
    if totals["discount"] > totals["subtotal"]:
        errors.append("invoice.discount_exceeds_subtotal")
    if totals["total"] < 0:
        errors.append("invoice.total_negative")
    if draft.concepts and totals["total"] == 0 and draft.cfdi_type == "I":
        warnings.append("invoice.total_is_zero")


def inspect_draft(draft: InvoiceDraft) -> dict[str, list[str]]:
    """Revision completa del borrador: `errors` bloquea el timbrado, `warnings` no."""
    errors: list[str] = []
    warnings: list[str] = []
    _validate_issuer(draft, errors, warnings)
    _validate_receiver(draft, errors, warnings)
    _validate_header(draft, errors, warnings)
    _validate_concepts(draft, errors, warnings)
    _validate_totals(draft, errors, warnings)
    return {"errors": errors, "warnings": warnings}


def validate_draft(draft: InvoiceDraft) -> list[str]:
    """Errores que impiden timbrar. Vacio = el borrador es apto para el PAC."""
    return inspect_draft(draft)["errors"]
