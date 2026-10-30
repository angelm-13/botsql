from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from app.utils.errors import AppError
from app.validations.registry import VALIDATION_RULES

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
PHONE_RE = re.compile(r"^\+?[0-9][0-9\s().-]{6,19}$")
MX_TAX_ID_RE = re.compile(r"^[A-ZÑ&]{3,4}[0-9]{6}[A-Z0-9]{3}$", re.IGNORECASE)


def _is_empty(value: Any) -> bool:
    return value is None or (isinstance(value, str) and value.strip() == "")


def _fail(entity: str, field: str, rule: dict[str, Any]) -> None:
    raise AppError(
        rule.get("message_key") or "errors.validation_failed",
        status_code=400,
        meta={
            "entity": entity,
            "field": field,
            "validation_type": rule.get("validation_type"),
            "rule": rule.get("rule"),
            "severity": rule.get("severity", "error"),
            "graphql_error_code": rule.get("graphql_error_code", ""),
        },
    )


def _to_decimal(value: Any) -> Decimal | None:
    if _is_empty(value):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _to_datetime(value: Any) -> datetime | None:
    if _is_empty(value):
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            try:
                return datetime.fromisoformat(value.split("T", 1)[0].split(" ", 1)[0])
            except ValueError:
                return None
    return None


def _compare(left: Any, op: str, right: Any) -> bool:
    if left is None or right is None:
        return True
    if op == ">=":
        return left >= right
    if op == "<=":
        return left <= right
    if op == ">":
        return left > right
    if op == "<":
        return left < right
    if op in {"=", "=="}:
        return left == right
    if op == "!=":
        return left != right
    return True


def _validate_required(entity: str, field: str, payload: dict[str, Any], rule: dict[str, Any], partial: bool) -> None:
    if partial and field not in payload:
        return
    if _is_empty(payload.get(field)):
        _fail(entity, field, rule)


def _validate_range(entity: str, field: str, payload: dict[str, Any], rule: dict[str, Any]) -> None:
    value = _to_decimal(payload.get(field))
    if value is None:
        return
    rule_text = str(rule.get("rule") or "")
    match = re.search(r"value\s*(>=|<=|>|<|=|==|!=)\s*(-?\d+(?:\.\d+)?)", rule_text)
    if not match:
        return
    op, raw_limit = match.groups()
    if not _compare(value, op, Decimal(raw_limit)):
        _fail(entity, field, rule)


def _validate_format(entity: str, field: str, payload: dict[str, Any], rule: dict[str, Any]) -> None:
    value = payload.get(field)
    if _is_empty(value):
        return
    text = str(value).strip()
    rule_text = str(rule.get("rule") or "").lower()
    if rule_text.startswith("email") and not EMAIL_RE.match(text):
        _fail(entity, field, rule)
    if rule_text.startswith("phone") and not PHONE_RE.match(text):
        _fail(entity, field, rule)
    if "mx_rfc" in rule_text or "tax_id" in rule_text:
        if not MX_TAX_ID_RE.match(text):
            _fail(entity, field, rule)
    if rule_text.startswith("password"):
        checks = {
            "min8": len(text) >= 8,
            "upper": any(ch.isupper() for ch in text),
            "lower": any(ch.islower() for ch in text),
            "number": any(ch.isdigit() for ch in text),
            "special": any(not ch.isalnum() for ch in text),
        }
        if any(token in rule_text and not ok for token, ok in checks.items()):
            _fail(entity, field, rule)


def _validate_comparison(entity: str, field: str, payload: dict[str, Any], rule: dict[str, Any]) -> None:
    rule_text = str(rule.get("rule") or "")
    match = re.search(r"(\w+)\s*(>=|<=|>|<|=|==|!=)\s*(\w+)", rule_text)
    if not match:
        return
    left_field, op, right_field = match.groups()
    left = _to_datetime(payload.get(left_field)) or _to_decimal(payload.get(left_field))
    right = _to_datetime(payload.get(right_field)) or _to_decimal(payload.get(right_field))
    if left is None or right is None:
        return
    if not _compare(left, op, right):
        _fail(entity, field, rule)


def _validate_business(entity: str, field: str, payload: dict[str, Any], rule: dict[str, Any]) -> None:
    rule_text = str(rule.get("rule") or "")
    sum_match = re.search(r"(\w+)\s*=\s*(\w+)\s*\+\s*(\w+)", rule_text)
    if sum_match:
        target_field, left_field, right_field = sum_match.groups()
        target = _to_decimal(payload.get(target_field))
        left = _to_decimal(payload.get(left_field))
        right = _to_decimal(payload.get(right_field))
        if target is None or left is None or right is None:
            return
        esperado = left + right
        # En una factura el descuento sale del subtotal: total = subtotal - descuento + impuesto.
        if entity == "invoice" and target_field == "total":
            esperado -= _to_decimal(payload.get("descuento")) or Decimal("0")
        if target != esperado:
            _fail(entity, field, rule)
        return

    neq_match = re.search(r"(\w+)\s*!=\s*(\w+)", rule_text)
    if neq_match:
        left_field, right_field = neq_match.groups()
        left = payload.get(left_field)
        right = payload.get(right_field)
        if _is_empty(left) or _is_empty(right):
            return
        if left == right:
            _fail(entity, field, rule)
        return

    if "cannot equal" in rule_text and "id_task" in rule_text:
        dependency = payload.get("dependency")
        task_id = payload.get("id_task")
        if not _is_empty(dependency) and not _is_empty(task_id) and dependency == task_id:
            _fail(entity, field, rule)


def validate_payload(entity: str, payload: dict[str, Any], partial: bool = False) -> None:
    rules_by_field = VALIDATION_RULES.get(entity, {})
    for field, rules in rules_by_field.items():
        if partial and field not in payload:
            continue
        for rule in rules:
            validation_type = rule.get("validation_type")
            if validation_type == "required":
                _validate_required(entity, field, payload, rule, partial)
            elif validation_type == "range":
                _validate_range(entity, field, payload, rule)
            elif validation_type == "format":
                _validate_format(entity, field, payload, rule)
            elif validation_type == "comparison":
                _validate_comparison(entity, field, payload, rule)
            elif validation_type == "business":
                _validate_business(entity, field, payload, rule)
