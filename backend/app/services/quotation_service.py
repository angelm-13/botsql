from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from sqlalchemy import select

from app.models.invoice import Invoice
from app.models.invoice_material_service import InvoiceMaterialService
from app.models.task import Task
from app.models.session import transaction_context
from app.utils.errors import AppError


MONEY = Decimal("0.01")
STATUS_ALIASES = {"cotizacion": "draft", "cotización": "draft", "pendiente": "converted"}
TRANSITIONS = {
    "draft": {"sent"},
    "sent": {"partially_approved", "approved", "rejected"},
    "partially_approved": {"approved", "rejected"},
    "approved": {"converted"},
    "rejected": {"draft"},
    "converted": set(),
}


def normalize_status(value):
    status = str(value or "").strip().lower()
    return STATUS_ALIASES.get(status, status)


def is_expired(date_expiration, today=None):
    """Si una vigencia ya paso. `date_expiration` puede venir sin hora."""
    if not date_expiration:
        return False
    reference = today or date.today()
    if isinstance(date_expiration, datetime):
        date_expiration = date_expiration.date()
    elif isinstance(date_expiration, str):
        try:
            date_expiration = date.fromisoformat(date_expiration[:10])
        except ValueError:
            return False
    return date_expiration < reference


def ensure_not_expired(invoice):
    """Bloquea aceptar/convertir una cotizacion cuya vigencia ya paso.

    Ni cotizador_demo ni tyakxa_tny comparaban `date_expiration`/`validity_date`
    contra la fecha de hoy en ningun punto -el campo se capturaba pero nunca se
    hacia cumplir-. Se agrega aqui, en el punto donde de verdad importa: al
    aceptar (cliente) o convertir (staff) una cotizacion en factura, no al
    guardarla ni al listarla, porque una cotizacion vencida sigue siendo
    consultable, solo no debe poder volverse un compromiso de cobro.
    """
    date_expiration = invoice.get('date_expiration') if isinstance(invoice, dict) else getattr(invoice, 'date_expiration', None)
    if is_expired(date_expiration):
        raise AppError(
            'validations.invoice.quotation_expired',
            409,
            {'date_expiration': str(date_expiration)},
        )


def validate_transition(current_status, target_status):
    current = normalize_status(current_status)
    target = normalize_status(target_status)
    if current not in TRANSITIONS or target not in TRANSITIONS[current]:
        raise AppError(
            "errors.quotation_invalid_transition",
            409,
            {"current_status": current, "target_status": target},
        )
    return target


def _decimal(value, field):
    try:
        return Decimal(str(value or "0"))
    except InvalidOperation as exc:
        raise AppError("errors.invalid_field", 400, {"field": field}) from exc


def calculate_totals(lines, tax_rate=Decimal("0")):
    rate = _decimal(tax_rate, "tax_rate")
    if rate < 0 or rate > 100:
        raise AppError("errors.invalid_field", 400, {"field": "tax_rate"})

    subtotal = Decimal("0")
    discount = Decimal("0")
    for line in lines:
        quantity = _decimal(line.get("quantity"), "quantity")
        unit_price = _decimal(line.get("gross_price"), "gross_price")
        line_discount = _decimal(line.get("discount") or line.get("descuento"), "discount")
        if quantity <= 0 or unit_price < 0 or line_discount < 0:
            raise AppError("errors.invalid_field", 400, {"field": "quotation_line"})
        line_subtotal = quantity * unit_price
        if line_discount > line_subtotal:
            raise AppError("errors.invalid_field", 400, {"field": "discount"})
        subtotal += line_subtotal
        discount += line_discount

    taxable_base = subtotal - discount
    tax = taxable_base * rate / Decimal("100")
    return {
        "subtotal": subtotal.quantize(MONEY, rounding=ROUND_HALF_UP),
        "discount": discount.quantize(MONEY, rounding=ROUND_HALF_UP),
        "tax": tax.quantize(MONEY, rounding=ROUND_HALF_UP),
        "total": (taxable_base + tax).quantize(MONEY, rounding=ROUND_HALF_UP),
    }


def totals_from_priced_lines(lines, fallback_tax_rate=Decimal("0")):
    """Suma lo que CADA renglon ya trae calculado, en vez de recalcular todo
    contra una sola tasa del encabezado.

    Bug real corregido (2026-09-29): `calculate_totals(lines, tax_rate)`
    ignora por completo `tax_applicable`/`line_tax`/`tax_rate` de cada
    renglon -- aplica una tasa unica a todo el subtotal. Si al convertir una
    cotizacion el encabezado de la factura no trae `tax_rate` capturado (no
    es un campo obligatorio), el IVA que el cliente ya vio en su cotizacion
    desaparecia sin ningun error visible.

    Prioridad por renglon: se usa `line_tax` si ya viene capturado (es lo
    que el cliente vio y aprobo en la cotizacion, no se recalcula). Si falta,
    se calcula con la tasa PROPIA del renglon (`tax_rate`) cuando
    `tax_applicable` es verdadero. Solo si ninguno de los dos esta capturado
    se usa `fallback_tax_rate` -- el mismo comportamiento de antes, pero como
    ultimo recurso y no como unica fuente.
    """
    subtotal = Decimal("0")
    discount = Decimal("0")
    tax = Decimal("0")
    fallback_rate = _decimal(fallback_tax_rate, "tax_rate")

    for line in lines:
        quantity = _decimal(line.get("quantity"), "quantity")
        unit_price = _decimal(line.get("gross_price"), "gross_price")
        line_discount = _decimal(line.get("discount") or line.get("descuento"), "discount")
        if quantity <= 0 or unit_price < 0 or line_discount < 0:
            raise AppError("errors.invalid_field", 400, {"field": "quotation_line"})
        line_subtotal = quantity * unit_price
        if line_discount > line_subtotal:
            raise AppError("errors.invalid_field", 400, {"field": "discount"})
        subtotal += line_subtotal
        discount += line_discount

        if line.get("line_tax") is not None:
            tax += _decimal(line.get("line_tax"), "line_tax")
        elif line.get("tax_applicable"):
            renglon_rate = line.get("tax_rate")
            rate = _decimal(renglon_rate, "tax_rate") if renglon_rate is not None else fallback_rate
            tax += (line_subtotal - line_discount) * rate / Decimal("100")

    total = subtotal - discount + tax
    return {
        "subtotal": subtotal.quantize(MONEY, rounding=ROUND_HALF_UP),
        "discount": discount.quantize(MONEY, rounding=ROUND_HALF_UP),
        "tax": tax.quantize(MONEY, rounding=ROUND_HALF_UP),
        "total": total.quantize(MONEY, rounding=ROUND_HALF_UP),
    }


def link_line_to_task(line_id, task_id, user_data):
    with transaction_context() as db:
        line = db.get(InvoiceMaterialService, line_id)
        task = db.get(Task, task_id)
        if not line or not task:
            raise AppError("errors.resource_not_found", 404)
        invoice = db.get(Invoice, line.id_invoice)
        if not invoice or not invoice.id_proyect or invoice.id_proyect != task.id_proyect:
            raise AppError("errors.resource_scope_mismatch", 409)

        actor_project = user_data.get("id_proyect") or user_data.get("project_id")
        unrestricted = bool(user_data.get("is_superuser") or user_data.get("is_bootstrap_admin"))
        if not unrestricted and str(actor_project) != str(invoice.id_proyect):
            raise AppError("errors.permission_denied", 403)

        line.id_task = task.id_task
        db.flush()
        return line.serialize()