from __future__ import annotations
from functools import wraps
import os
from flask import jsonify, request
import jwt
from app.models import User
from app.models.session import transaction_context

SECRET_KEY = os.getenv('JWT_SECRET', 'dev-secret-change-me')
JWT_ALGORITHM = 'HS256'
PUBLIC_JWT_SCOPE = os.getenv('PUBLIC_JWT_SCOPE', 'web_shopper')


def _is_active_web_shopper(user: User) -> bool:
    if not user:
        return False
    if str(getattr(user, 'user_type', '') or '').strip().lower() != 'web_shopper':
        return False
    if getattr(user, 'deletion_date', None) is not None:
        return False
    status = getattr(user, 'id_status', 1)
    return str(status if status is not None else 1).strip() == '1'


def public_user_payload(user: User) -> dict:
    return {
        'id_user': getattr(user, 'id_user', None),
        'email': getattr(user, 'email', None) or getattr(user, 'username', None),
        'username': getattr(user, 'username', None),
        'full_name': getattr(user, 'full_name', None),
        'phone': getattr(user, 'principal_phone', None),
        'tax_id': getattr(user, 'tax_id', None),
        'accepts_marketing': bool(getattr(user, 'accepts_marketing', False)),
        'user_type': getattr(user, 'user_type', None),
        'scope': PUBLIC_JWT_SCOPE,
    }


def require_public_jwt(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        raw = request.headers.get('Authorization', '')
        token = raw.replace('Bearer ', '', 1).strip() if raw.startswith('Bearer ') else ''
        if not token:
            return jsonify({'error_key': 'errors.auth_required'}), 401
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
        except Exception:
            return jsonify({'error_key': 'errors.invalid_token'}), 401
        if str(payload.get('scope') or '').strip().lower() != str(PUBLIC_JWT_SCOPE).strip().lower():
            return jsonify({'error_key': 'errors.invalid_token'}), 401
        user_id = payload.get('id_user')
        with transaction_context() as db:
            user = db.get(User, user_id)
            if not _is_active_web_shopper(user):
                return jsonify({'error_key': 'errors.invalid_token'}), 401
            current = public_user_payload(user)
        return fn(current, *args, **kwargs)
    return wrapper
