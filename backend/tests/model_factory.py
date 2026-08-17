from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from sqlalchemy import Boolean, Date, DateTime, Enum, Integer, JSON, LargeBinary, Numeric, String


FIXED_DATE = date(2026, 1, 15)
FIXED_DATETIME = datetime(2026, 1, 15, 12, 0, 0)


def _value_for_type(column_type, value=None):
    if isinstance(column_type, DateTime):
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace('Z', '+00:00')).replace(tzinfo=None)
            except ValueError:
                pass
        return FIXED_DATETIME
    if isinstance(column_type, Date):
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            try:
                return date.fromisoformat(value.split('T', 1)[0])
            except ValueError:
                pass
        return FIXED_DATE
    if isinstance(column_type, Boolean):
        return value if isinstance(value, bool) else True
    if isinstance(column_type, Integer):
        try:
            return int(value) if value is not None else 1
        except (TypeError, ValueError):
            return 1
    if isinstance(column_type, Numeric):
        try:
            return Decimal(str(value)) if value is not None else Decimal('1')
        except (InvalidOperation, TypeError, ValueError):
            return Decimal('1')
    if isinstance(column_type, Enum):
        return value if value in column_type.enums else column_type.enums[0]
    if isinstance(column_type, LargeBinary):
        if isinstance(value, bytes):
            return value
        return str(value or 'test').encode('utf-8')
    if isinstance(column_type, JSON):
        if not isinstance(value, str):
            return value if value is not None else {}
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return {}
    if isinstance(column_type, String):
        text = str(value if value is not None else 'test')
        return text[:column_type.length] if column_type.length else text
    return value if value is not None else 1


def build_model(model_class, **overrides):
    return model_class(**build_model_values(model_class, overrides))


def build_model_values(model_class, overrides=None):
    overrides = dict(overrides or {})
    values = {}
    for column in model_class.__table__.columns:
        if column.primary_key and column.autoincrement:
            continue
        supplied = column.name in overrides
        if not supplied and (column.nullable or column.default is not None or column.server_default is not None):
            continue
        values[column.name] = _value_for_type(column.type, overrides.get(column.name))
    return values


def build_payload(service_class, overrides=None, **extra_overrides):
    values = dict(overrides or {})
    values.update(extra_overrides)
    return build_model_values(service_class.model, values)