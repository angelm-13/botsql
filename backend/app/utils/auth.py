from __future__ import annotations
from functools import wraps
from flask import jsonify, request
import jwt
import os

PERMISSION_BITS = {'create': 1, 'read': 2, 'update': 4, 'delete': 8}
SECRET_KEY = os.getenv('JWT_SECRET', 'dev-secret-change-me')
PUBLIC_JWT_SCOPE = os.getenv('PUBLIC_JWT_SCOPE', 'web_shopper')
BOOTSTRAP_ONLY_ENTITIES = {'event_log', 'user_mfa', 'password_reset_token'}
ADMIN_PERMISSION_ENTITIES = {'permission', 'entity_permission', 'nm_field_permission', 'field'}
ADMIN_PERMISSION_READ_ENTITIES = ADMIN_PERMISSION_ENTITIES | {'user', 'department', 'subdepartment', 'level'}


def token_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'error_key': 'errors.auth_required'}), 401
        try:
            user_data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        except Exception:
            return jsonify({'error_key': 'errors.invalid_token'}), 401
        if str(user_data.get('scope') or '').strip().lower() == str(PUBLIC_JWT_SCOPE).strip().lower():
            return jsonify({'error_key': 'errors.invalid_token'}), 401
        return fn(user_data, *args, **kwargs)
    return wrapper


def _is_superuser(user_data: dict) -> bool:
    return bool(user_data.get('is_superuser') or user_data.get('is_bootstrap_admin'))


def _get_permission_id(user_data: dict):
    value = user_data.get('id_permission') or user_data.get('permission_id')
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _has_entity_permission(user_data: dict, entity_name: str, action: str) -> bool:
    if _is_superuser(user_data):
        return True

    if entity_name in BOOTSTRAP_ONLY_ENTITIES:
        return False

    bit = PERMISSION_BITS.get(action)
    if bit is None:
        return False

    permission_id = _get_permission_id(user_data)
    if not permission_id:
        return False

    from app.models.entity_permission import EntityPermission
    from app.models.session import transaction_context

    with transaction_context() as db_session:
        record = (
            db_session.query(EntityPermission)
            .filter(EntityPermission.id_permission == permission_id)
            .filter(EntityPermission.entity_name == entity_name)
            .filter(EntityPermission.deletion_date.is_(None))
            .first()
        )
        if not record:
            return False
        try:
            control_type = int(record.control_type)
        except (TypeError, ValueError):
            return False
        return (control_type & bit) == bit


def require_entity_permission(entity_name: str, action: str):
    def decorator(fn):
        @wraps(fn)
        def wrapper(user_data, *args, **kwargs):
            if not _has_entity_permission(user_data, entity_name, action):
                return jsonify({'error_key': 'errors.permission_denied', 'meta': {'entity': entity_name, 'action': action}}), 403
            return fn(user_data, *args, **kwargs)
        return wrapper
    return decorator
