from __future__ import annotations
from datetime import datetime, timezone
from flask import Blueprint, jsonify, request
from sqlalchemy import or_
from app.models import User, EventLog
from app.models.session import transaction_context
from app.utils.auth import token_required, require_entity_permission
from app.utils.errors import AppError


bp_web_shoppers = Blueprint('web_shoppers', __name__, url_prefix='/web-shoppers')
ACTIVE_STATUS_ID = 1
INACTIVE_STATUS_ID = 2


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _to_int(value, default=None):
    try:
        if value in (None, ''):
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _last_login_at(session, user_id):
    if not user_id:
        return None
    row = (
        session.query(EventLog.creation_date)
        .filter(EventLog.table_name == 'web_shopper')
        .filter(EventLog.field_name == 'web_shopper.login_success')
        .filter(EventLog.created_by == user_id)
        .order_by(EventLog.creation_date.desc())
        .first()
    )
    return row[0] if row else None


def _serialize_web_shopper(user: User, session=None) -> dict:
    status_id = getattr(user, 'id_status', None)
    last_login = _last_login_at(session, getattr(user, 'id_user', None)) if session is not None else None
    return {
        'id_user': getattr(user, 'id_user', None),
        'email': getattr(user, 'email', None) or getattr(user, 'username', None),
        'username': getattr(user, 'username', None),
        'full_name': getattr(user, 'full_name', None),
        'first_name': getattr(user, 'first_name', None),
        'last_name_father': getattr(user, 'last_name_father', None),
        'last_name_mother': getattr(user, 'last_name_mother', None),
        'phone': getattr(user, 'principal_phone', None),
        'principal_phone': getattr(user, 'principal_phone', None),
        'tax_id': getattr(user, 'tax_id', None),
        'id_status': status_id,
        'is_active': str(status_id if status_id is not None else ACTIVE_STATUS_ID).strip() == str(ACTIVE_STATUS_ID),
        'accepts_marketing': bool(getattr(user, 'accepts_marketing', False)),
        'creation_date': getattr(user, 'creation_date', None).isoformat() if getattr(user, 'creation_date', None) else None,
        'last_update_date': getattr(user, 'last_update_date', None).isoformat() if getattr(user, 'last_update_date', None) else None,
        'last_login_at': last_login.isoformat() if last_login else None,
        'total_orders': 0,
    }


def _query_web_shoppers(session):
    return (
        session.query(User)
        .filter(User.user_type == 'web_shopper')
        .filter(User.deletion_date.is_(None))
    )


def _get_web_shopper_or_404(session, id_user: int) -> User:
    user = (
        _query_web_shoppers(session)
        .filter(User.id_user == id_user)
        .first()
    )
    if not user:
        raise AppError('errors.resource_not_found', 404)
    return user


@bp_web_shoppers.route('', methods=['GET'])
@bp_web_shoppers.route('/', methods=['GET'])
@token_required
@require_entity_permission('user', 'read')
def list_web_shoppers(user_data):
    page = max(_to_int(request.args.get('page'), 1), 1)
    per_page = min(max(_to_int(request.args.get('per_page'), 20), 1), 100)
    search = str(request.args.get('search') or '').strip()
    active = str(request.args.get('active') or '').strip().lower()

    with transaction_context() as session:
        query = _query_web_shoppers(session)

        if search:
            pattern = f'%{search}%'
            query = query.filter(or_(
                User.email.ilike(pattern),
                User.username.ilike(pattern),
                User.full_name.ilike(pattern),
                User.principal_phone.ilike(pattern),
                User.tax_id.ilike(pattern),
            ))

        if active in {'true', '1', 'active', 'activo'}:
            query = query.filter(User.id_status == ACTIVE_STATUS_ID)
        elif active in {'false', '0', 'inactive', 'inactivo'}:
            query = query.filter(User.id_status != ACTIVE_STATUS_ID)

        total = query.count()
        rows = (
            query
            .order_by(User.id_user.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        items = [_serialize_web_shopper(row, session) for row in rows]

    return jsonify({'items': items, 'total': total, 'page': page, 'per_page': per_page, 'pages': (total + per_page - 1) // per_page})


@bp_web_shoppers.route('/<int:id_user>', methods=['GET'])
@token_required
@require_entity_permission('user', 'read')
def get_web_shopper(user_data, id_user):
    with transaction_context() as session:
        user = _get_web_shopper_or_404(session, id_user)
        return jsonify(_serialize_web_shopper(user, session))


@bp_web_shoppers.route('/<int:id_user>/deactivate', methods=['PATCH', 'POST'])
@token_required
@require_entity_permission('user', 'update')
def deactivate_web_shopper(user_data, id_user):
    with transaction_context() as session:
        user = _get_web_shopper_or_404(session, id_user)
        user.id_status = INACTIVE_STATUS_ID
        user.last_update_date = _now()
        session.flush()
        return jsonify(_serialize_web_shopper(user, session))


@bp_web_shoppers.route('/<int:id_user>/reactivate', methods=['PATCH', 'POST'])
@token_required
@require_entity_permission('user', 'update')
def reactivate_web_shopper(user_data, id_user):
    with transaction_context() as session:
        user = _get_web_shopper_or_404(session, id_user)
        user.id_status = ACTIVE_STATUS_ID
        user.last_update_date = _now()
        session.flush()
        return jsonify(_serialize_web_shopper(user, session))
