
from __future__ import annotations

from datetime import datetime, UTC
from typing import Any

from sqlalchemy import select, func

from app.models.session import transaction_context


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def result_ok(message_key: str, **payload: Any) -> dict[str, Any]:
    return {"ok": True, "message_key": message_key, "finished_at": utc_now_iso(), **payload}


def result_error(message_key: str, **payload: Any) -> dict[str, Any]:
    return {"ok": False, "message_key": message_key, "finished_at": utc_now_iso(), **payload}


def count_model(model: type, filters: list[Any] | None = None) -> int:
    with transaction_context() as session:
        stmt = select(func.count()).select_from(model)
        if filters:
            stmt = stmt.filter(*filters)
        return int(session.scalar(stmt) or 0)


def fetch_batch(model: type, page: int = 1, per_page: int = 500) -> list[Any]:
    offset = max(page - 1, 0) * per_page
    with transaction_context() as session:
        return list(session.scalars(select(model).offset(offset).limit(per_page)).all())
