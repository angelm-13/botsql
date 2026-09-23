
from __future__ import annotations

from enum import IntEnum
from functools import wraps
from typing import Any, Callable

from flask import jsonify, g


class PermissionAction(IntEnum):
    CREATE = 1
    READ = 2
    UPDATE = 4
    DELETE = 8


ACTION_TO_I18N_KEY = {
    PermissionAction.CREATE: "security.permission.create_denied",
    PermissionAction.READ: "security.permission.read_denied",
    PermissionAction.UPDATE: "security.permission.update_denied",
    PermissionAction.DELETE: "security.permission.delete_denied",
}

# Cada accion vive en su propia columna de alcance (0 Sin acceso, 1 Propios,
# 2 Mis grupos, 4 Todos -- ver entity_permission.py). El gate de aqui sigue
# siendo booleano: 0 deniega, cualquier otro valor permite. El alcance real
# (que Propios/Mis grupos filtren de verdad lo que se ve) no esta conectado
# todavia -- es trabajo de una fase aparte, ver ARQUITECTURA_TYAKXA_TNY.md.
ACTION_TO_SCOPE_COLUMN = {
    PermissionAction.CREATE: "scope_create",
    PermissionAction.READ: "scope_read",
    PermissionAction.UPDATE: "scope_update",
    PermissionAction.DELETE: "scope_delete",
}


def _get_user_permission_id(user_data: dict[str, Any]) -> int | None:
    value = user_data.get("id_permission") or user_data.get("permission_id")
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def has_permission(db_session: Any, user_data: dict[str, Any], entity_name: str, action: PermissionAction) -> bool:
    permission_id = _get_user_permission_id(user_data)
    if not permission_id:
        return False

    from app.models.entity_permission import EntityPermission

    record = (
        db_session.query(EntityPermission)
        .filter(EntityPermission.id_permission == permission_id)
        .filter(EntityPermission.entity_name == entity_name)
        .filter(EntityPermission.deletion_date.is_(None))
        .first()
    )
    if not record:
        return False
    scope_column = ACTION_TO_SCOPE_COLUMN[action]
    return int(getattr(record, scope_column)) != 0


def require_entity_permission(entity_name: str, action: PermissionAction) -> Callable:
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(user_data, *args, **kwargs):
            from app.models.session import transaction_context
            from app.security.audit import audit_event

            with transaction_context() as db_session:
                allowed = has_permission(db_session, user_data, entity_name, action)
                if not allowed:
                    audit_event(
                        db_session=db_session,
                        user_data=user_data,
                        event_type="permission_denied",
                        entity_name=entity_name,
                        action=action.name.lower(),
                        metadata={"route": getattr(fn, "__name__", "unknown")},
                    )
                    return jsonify({
                        "error": "permission_denied",
                        "message_key": ACTION_TO_I18N_KEY[action],
                        "entity": entity_name,
                        "action": action.name.lower(),
                    }), 403

                g.security_entity = entity_name
                g.security_action = action.name.lower()

            return fn(user_data, *args, **kwargs)
        return wrapper
    return decorator


def require_create_permission(entity_name: str) -> Callable:
    return require_entity_permission(entity_name, PermissionAction.CREATE)


def require_read_permission(entity_name: str) -> Callable:
    return require_entity_permission(entity_name, PermissionAction.READ)


def require_update_permission(entity_name: str) -> Callable:
    return require_entity_permission(entity_name, PermissionAction.UPDATE)


def require_delete_permission(entity_name: str) -> Callable:
    return require_entity_permission(entity_name, PermissionAction.DELETE)
