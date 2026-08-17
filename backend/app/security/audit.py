
from __future__ import annotations

from typing import Any


def audit_event(
    db_session: Any,
    user_data: dict[str, Any] | None,
    event_type: str,
    entity_name: str | None = None,
    action: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    from app.models.audit_log import AuditLog

    user_data = user_data or {}
    event = AuditLog(
        id_user=user_data.get("id_user"),
        event_type=event_type,
        entity_name=entity_name,
        action=action,
        metadata_json=metadata or {},
    )
    db_session.add(event)
