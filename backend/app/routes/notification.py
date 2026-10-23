from __future__ import annotations
from flask import Blueprint, jsonify, request

from app.models.notification import Notification
from app.models.session import transaction_context
from app.services.notification_service import NotificationService
from app.utils.auth import require_entity_permission, token_required
from app.utils.errors import AppError

bp_notification = Blueprint('notification', __name__, url_prefix='/notification')


def _actor_id(user_data: dict) -> int:
    value = user_data.get('id_user') or user_data.get('user_id')
    try:
        actor_id = int(value) if value is not None else None
    except (TypeError, ValueError):
        actor_id = None
    if not actor_id:
        raise AppError('errors.auth_required', 401)
    return actor_id


@bp_notification.get('/')
@token_required
@require_entity_permission('notification', 'read')
def list_notifications(user_data):
    """Siempre las propias -- una notificacion no se lista "de todos"."""
    page = int(request.args.get('page', 1))
    per_page = min(max(int(request.args.get('per_page', 20)), 1), 100)
    actor_id = _actor_id(user_data)
    with transaction_context() as db:
        query = db.query(Notification).filter(Notification.id_user == actor_id)
        total = query.count()
        items = (
            query.order_by(Notification.creation_date.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        payload = {
            'items': [item.serialize() for item in items],
            'total': total, 'page': page, 'per_page': per_page,
            'pages': (total + per_page - 1) // per_page,
        }
    return jsonify(payload)


@bp_notification.get('/unread-count')
@token_required
@require_entity_permission('notification', 'read')
def unread_notification_count(user_data):
    return jsonify({'unread_count': NotificationService.unread_count(_actor_id(user_data))})


@bp_notification.patch('/<int:id_notification>/read')
@token_required
@require_entity_permission('notification', 'read')
def mark_notification_read(user_data, id_notification):
    return jsonify(NotificationService.mark_read(id_notification, _actor_id(user_data)))


@bp_notification.patch('/read-all')
@token_required
@require_entity_permission('notification', 'read')
def mark_all_notifications_read(user_data):
    return jsonify(NotificationService.mark_all_read(_actor_id(user_data)))
