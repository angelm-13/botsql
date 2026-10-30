from __future__ import annotations

from flask import Blueprint, jsonify, request

from app.services.notification_service import (
    create_notification,
    get_user_notifications,
    get_notification_by_id,
    mark_as_read,
    mark_all_as_read,
    delete_notification,
    get_unread_count,
)
from app.utils.auth import token_required
from app.utils.errors import AppError


bp_notifications = Blueprint("notifications", __name__, url_prefix="/notifications")


@bp_notifications.route("", methods=["GET"])
@token_required
def get_notifications(user_data):
    """
    GET /notifications?unread=true&limit=50&offset=0

    Obtiene las notificaciones del usuario actual.
    Parámetros opcionales:
    - unread: Si es true, solo obtiene notificaciones no leídas
    - limit: Máximo de resultados (default 50)
    - offset: Desplazamiento para paginación (default 0)
    """
    id_user = user_data.get('id_user')
    if not id_user:
        raise AppError("Usuario no autenticado", 401)

    unread_only = request.args.get('unread', 'false').lower() == 'true'
    limit = min(int(request.args.get('limit', 50)), 100)
    offset = int(request.args.get('offset', 0))

    notifications = get_user_notifications(
        id_user=id_user,
        unread_only=unread_only,
        limit=limit,
        offset=offset,
    )

    return jsonify([n.serialize() for n in notifications])


@bp_notifications.route("/unread-count", methods=["GET"])
@token_required
def get_notifications_unread_count(user_data):
    """
    GET /notifications/unread-count

    Obtiene el contador de notificaciones no leídas (para el badge en topbar).
    """
    id_user = user_data.get('id_user')
    if not id_user:
        raise AppError("Usuario no autenticado", 401)

    count = get_unread_count(id_user)
    return jsonify({'unread_count': count})


@bp_notifications.route("/<int:id_notification>", methods=["GET"])
@token_required
def get_notification(user_data, id_notification):
    """
    GET /notifications/{id}

    Obtiene una notificación específica.
    """
    notification = get_notification_by_id(id_notification)

    if not notification:
        raise AppError("Notificación no encontrada", 404)

    id_user = user_data.get('id_user')
    if notification.id_user_recipient != id_user:
        raise AppError("No tienes permiso para ver esta notificación", 403)

    return jsonify(notification.serialize())


@bp_notifications.route("/<int:id_notification>/read", methods=["PUT"])
@token_required
def mark_notification_as_read(user_data, id_notification):
    """
    PUT /notifications/{id}/read

    Marca una notificación como leída.
    """
    id_user = user_data.get('id_user')
    if not id_user:
        raise AppError("Usuario no autenticado", 401)

    success = mark_as_read(id_notification, id_user)

    if not success:
        raise AppError("Notificación no encontrada o no te pertenece", 404)

    notification = get_notification_by_id(id_notification)
    return jsonify(notification.serialize() if notification else {})


@bp_notifications.route("/read-all", methods=["PUT"])
@token_required
def mark_all_notifications_as_read(user_data):
    """
    PUT /notifications/read-all

    Marca todas las notificaciones del usuario como leídas.
    """
    id_user = user_data.get('id_user')
    if not id_user:
        raise AppError("Usuario no autenticado", 401)

    count = mark_all_as_read(id_user)
    return jsonify({'marked_count': count})


@bp_notifications.route("/<int:id_notification>", methods=["DELETE"])
@token_required
def delete_single_notification(user_data, id_notification):
    """
    DELETE /notifications/{id}

    Elimina (soft delete) una notificación.
    """
    id_user = user_data.get('id_user')
    if not id_user:
        raise AppError("Usuario no autenticado", 401)

    success = delete_notification(id_notification, id_user)

    if not success:
        raise AppError("Notificación no encontrada o no te pertenece", 404)

    return jsonify({'message': 'Notificación eliminada'}), 200
