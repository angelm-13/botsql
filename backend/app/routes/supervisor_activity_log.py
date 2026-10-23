from __future__ import annotations
from flask import Blueprint, jsonify, request

from app.services.supervisor_activity_log_service import SupervisorActivityLogService, sees_every_log
from app.utils.auth import require_entity_permission, token_required
from app.utils.errors import AppError

bp_supervisor_activity_log = Blueprint('supervisor_activity_log', __name__, url_prefix='/supervisor_activity_log')
ALLOWED_FIELDS = {'id_supervisor_activity_log', 'id_user', 'activity_date', 'content', 'id_proyect'}


def _actor_id(user_data: dict) -> int:
    value = user_data.get('id_user') or user_data.get('user_id')
    try:
        actor_id = int(value) if value is not None else None
    except (TypeError, ValueError):
        actor_id = None
    if not actor_id:
        raise AppError('errors.auth_required', 401)
    return actor_id


@bp_supervisor_activity_log.get('/')
@token_required
@require_entity_permission('supervisor_activity_log', 'read')
def list_supervisor_activity_log(user_data):
    filters = {key: value for key, value in request.args.items() if key in ALLOWED_FIELDS}
    if not sees_every_log(user_data):
        filters['id_user'] = _actor_id(user_data)
    return jsonify(SupervisorActivityLogService.list(
        page=int(request.args.get('page', 1)),
        per_page=int(request.args.get('per_page', 20)),
        filters=filters,
        sort=request.args.get('sort'),
    ))


@bp_supervisor_activity_log.get('/<int:id_supervisor_activity_log>')
@token_required
@require_entity_permission('supervisor_activity_log', 'read')
def get_supervisor_activity_log(user_data, id_supervisor_activity_log):
    record = SupervisorActivityLogService.get(id_supervisor_activity_log)
    if not sees_every_log(user_data) and int(record.get('id_user') or 0) != _actor_id(user_data):
        raise AppError('errors.resource_not_found', status_code=404)
    return jsonify(record)


@bp_supervisor_activity_log.post('/')
@token_required
@require_entity_permission('supervisor_activity_log', 'create')
def create_supervisor_activity_log(user_data):
    payload = dict(request.get_json() or {})
    # Se captura siempre a nombre de quien la escribe -- no hay forma de
    # capturar la bitacora de otro usuario, aunque el rol vea la de todos.
    payload['id_user'] = _actor_id(user_data)
    return jsonify(SupervisorActivityLogService.create(payload, user_id=user_data.get('id_user'))), 201


@bp_supervisor_activity_log.put('/<int:id_supervisor_activity_log>')
@token_required
@require_entity_permission('supervisor_activity_log', 'update')
def update_supervisor_activity_log(user_data, id_supervisor_activity_log):
    current = SupervisorActivityLogService.get(id_supervisor_activity_log)
    if int(current.get('id_user') or 0) != _actor_id(user_data):
        raise AppError('errors.resource_not_found', status_code=404)
    payload = dict(request.get_json() or {})
    payload.pop('id_user', None)
    return jsonify(SupervisorActivityLogService.update(id_supervisor_activity_log, payload, user_id=user_data.get('id_user')))


@bp_supervisor_activity_log.delete('/<int:id_supervisor_activity_log>')
@token_required
@require_entity_permission('supervisor_activity_log', 'delete')
def delete_supervisor_activity_log(user_data, id_supervisor_activity_log):
    current = SupervisorActivityLogService.get(id_supervisor_activity_log)
    if int(current.get('id_user') or 0) != _actor_id(user_data):
        raise AppError('errors.resource_not_found', status_code=404)
    return jsonify(SupervisorActivityLogService.delete(id_supervisor_activity_log, user_id=user_data.get('id_user')))
