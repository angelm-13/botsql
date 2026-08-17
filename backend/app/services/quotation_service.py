from __future__ import annotations

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