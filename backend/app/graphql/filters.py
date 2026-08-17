from __future__ import annotations

from sqlalchemy import String, cast

ALLOWED_OPERATORS = {"eq", "contains", "startswith", "endswith", "gt", "gte", "lt", "lte"}


def apply_filters(query, model, filters: dict | None):
    if not filters:
        return query

    for raw_key, value in filters.items():
        if value in (None, ""):
            continue
        if "__" in raw_key:
            field_name, operator = raw_key.split("__", 1)
        else:
            field_name, operator = raw_key, "eq"
        if operator not in ALLOWED_OPERATORS or not hasattr(model, field_name):
            continue
        column = getattr(model, field_name)
        if operator == "eq":
            query = query.filter(column == value)
        elif operator == "contains":
            query = query.filter(cast(column, String).ilike(f"%{value}%"))
        elif operator == "startswith":
            query = query.filter(cast(column, String).ilike(f"{value}%"))
        elif operator == "endswith":
            query = query.filter(cast(column, String).ilike(f"%{value}"))
        elif operator == "gt":
            query = query.filter(column > value)
        elif operator == "gte":
            query = query.filter(column >= value)
        elif operator == "lt":
            query = query.filter(column < value)
        elif operator == "lte":
            query = query.filter(column <= value)
    return query
