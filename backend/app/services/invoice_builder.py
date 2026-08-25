from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from decimal import Decimal, ROUND_HALF_UP


MONEY = Decimal("0.01")
RFC_PATTERN = re.compile(r"^[A-ZÑ&]{3,4}[0-9]{6}[A-Z0-9]{3}$", re.IGNORECASE)
CP_PATTERN = re.compile(r"^[0-9]{5}$")
VALID_PAYMENT_METHODS = {"PUE", "PPD"}
VALID_PAYMENT_FORMS = {
    "01", "02", "03", "04", "05", "06", "08", "12", "13", "14", "15",
    "17", "23", "24", "25", "26", "27", "28", "29", "30", "31", "99",
}


def _decimal(value) -> Decimal:
    return Decimal(str(value or 0))


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)


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

    def serialize(self) -> dict:
        def convert(value):
            if isinstance(value, Decimal):
                return format(value, "f")
            if isinstance(value, list):
                return [convert(item) for item in value]
            if isinstance(value, dict):
                return {key: convert(item) for key, item in value.items()}
            return value

        return convert(asdict(self))


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
                sat_unit_key=str(line.sat_unit_key or "").strip(),
                tax_object=str(line.tax_object or ("02" if line.tax_applicable else "01")),
                discount=_money(_decimal(line.discount)),
                iva_rate=_decimal(line.tax_rate) / Decimal("100") if _decimal(line.tax_rate) > 1 else _decimal(line.tax_rate),
                isr_retention_rate=_decimal(line.isr_retention_rate) / Decimal("100") if _decimal(line.isr_retention_rate) > 1 else _decimal(line.isr_retention_rate),
                iva_retention_rate=_decimal(line.iva_retention_rate) / Decimal("100") if _decimal(line.iva_retention_rate) > 1 else _decimal(line.iva_retention_rate),
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
        payment_method=str(invoice.metodo_pago or "").strip(),
        currency=str(invoice.currency or "MXN").strip().upper(),
        exchange_rate=_decimal(invoice.type_exchange_rate or 1),
        payment_conditions=str(invoice.condiciones_pago or "").strip(),
        series=str(invoice.fiscal_certify_serie or invoice.serie_csd or "").strip(),
        folio=str(invoice.folio or "").strip(),
    )


def validate_draft(draft: InvoiceDraft) -> list[str]:
    errors = []
    if not RFC_PATTERN.match(draft.issuer.rfc):
        errors.append("invoice.issuer_rfc_invalid")
    if not draft.issuer.name:
        errors.append("invoice.issuer_name_required")
    if not draft.issuer.tax_regime:
        errors.append("invoice.issuer_tax_regime_required")
    if not CP_PATTERN.match(draft.issuer.postal_code):
        errors.append("invoice.issuer_postal_code_invalid")
    if not RFC_PATTERN.match(draft.receiver.rfc):
        errors.append("invoice.receiver_rfc_invalid")
    if not draft.receiver.name:
        errors.append("invoice.receiver_name_required")
    if not draft.receiver.tax_regime:
        errors.append("invoice.receiver_tax_regime_required")
    if not CP_PATTERN.match(draft.receiver.postal_code):
        errors.append("invoice.receiver_postal_code_invalid")
    if not draft.receiver.cfdi_use:
        errors.append("invoice.cfdi_use_required")
    if draft.payment_form not in VALID_PAYMENT_FORMS:
        errors.append("invoice.payment_form_invalid")
    if draft.payment_method not in VALID_PAYMENT_METHODS:
        errors.append("invoice.payment_method_invalid")
    if draft.payment_method == "PPD" and draft.payment_form != "99":
        errors.append("invoice.ppd_requires_payment_form_99")
    if not draft.concepts:
        errors.append("invoice.concepts_required")
    for index, concept in enumerate(draft.concepts):
        if not concept.description:
            errors.append(f"invoice.concepts.{index}.description_required")
        if concept.quantity <= 0 or concept.unit_price < 0:
            errors.append(f"invoice.concepts.{index}.amount_invalid")
        if not concept.sat_product_key:
            errors.append(f"invoice.concepts.{index}.sat_product_key_required")
        if not concept.sat_unit_key:
            errors.append(f"invoice.concepts.{index}.sat_unit_key_required")
        if concept.discount < 0 or concept.discount > concept.amount:
            errors.append(f"invoice.concepts.{index}.discount_invalid")
    return errors


def draft_totals(draft: InvoiceDraft) -> dict[str, Decimal]:
    subtotal = sum((concept.amount for concept in draft.concepts), Decimal("0"))
    discount = sum((concept.discount for concept in draft.concepts), Decimal("0"))
    iva = Decimal("0")
    isr_retention = Decimal("0")
    iva_retention = Decimal("0")
    for concept in draft.concepts:
        base = concept.amount - concept.discount
        if concept.tax_object != "01":
            iva += base * concept.iva_rate
            isr_retention += base * concept.isr_retention_rate
            iva_retention += base * concept.iva_retention_rate
    total = subtotal - discount + iva - isr_retention - iva_retention
    return {
        "subtotal": _money(subtotal),
        "discount": _money(discount),
        "iva": _money(iva),
        "isr_retention": _money(isr_retention),
        "iva_retention": _money(iva_retention),
        "total": _money(total),
    }