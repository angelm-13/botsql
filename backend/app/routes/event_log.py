from __future__ import annotations
from flask import Blueprint, jsonify, request
from app.services.event_log_service import EventLogService
from app.utils.auth import token_required, require_entity_permission
from app.utils.errors import AppError
import os


bp_event_log = Blueprint('event_log', __name__, url_prefix='/event_log')
ALLOWED_FIELDS = ['id_event_log', 'table_name', 'field_name', 'action', 'before_value', 'after_value', 'created_by', 'creation_date', 'last_update_date', 'deletion_date']

TECHNICAL_RESPONSE_FIELDS = {'id_event_log'}
FIELD_READ_BIT = 2


def _actor_has_unrestricted_field_access(user_data: dict) -> bool:
    return bool(
        user_data.get('is_superuser')
        or user_data.get('is_bootstrap_admin')
        or user_data.get('user_type') == 'admin'
    )


def _safe_int_value(value):
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _visible_response_fields_for_actor(user_data: dict) -> set[str]:
    if _actor_has_unrestricted_field_access(user_data):
        return set(ALLOWED_FIELDS)

    permission_id = _safe_int_value(user_data.get('id_permission') or user_data.get('permission_id'))
    if not permission_id:
        return set(TECHNICAL_RESPONSE_FIELDS)

    from app.models.field import Field
    from app.models.nm_field_permission import NmFieldPermission
    from app.models.session import transaction_context

    visible = set()
    with transaction_context() as db_session:
        rows = (
            db_session.query(NmFieldPermission, Field)
            .join(Field, NmFieldPermission.id_field == Field.id_field)
            .filter(NmFieldPermission.id_permission == permission_id)
            .filter(NmFieldPermission.deletion_date.is_(None))
            .filter(Field.table_name == 'event_log')
            .filter(Field.deletion_date.is_(None))
            .all()
        )
        for permission_row, field_row in rows:
            try:
                control_type = int(permission_row.control_type)
            except (TypeError, ValueError):
                continue
            if (control_type & FIELD_READ_BIT) == FIELD_READ_BIT:
                visible.add(field_row.field_name)

    # La llave primaria puede viajar en la respuesta para navegacion interna,
    # acciones de fila y rutas REST, aunque el frontend no la pinte si no fue
    # marcada como visible en el gestor.
    return visible | set(TECHNICAL_RESPONSE_FIELDS)


def _filter_payload_for_actor(payload: dict, user_data: dict) -> dict:
    payload = dict(payload or {})
    if _actor_has_unrestricted_field_access(user_data):
        return payload
    writable_fields = _visible_response_fields_for_actor(user_data) - set(TECHNICAL_RESPONSE_FIELDS)
    return {key: value for key, value in payload.items() if key in writable_fields}


def _project_record_payload(record: dict | None, visible_fields: set[str]) -> dict | None:
    if record is None:
        return record
    return {key: value for key, value in dict(record).items() if key in visible_fields}


def _project_list_payload(payload: dict, visible_fields: set[str]) -> dict:
    result = dict(payload or {})
    result['items'] = [
        _project_record_payload(item, visible_fields)
        for item in result.get('items', [])
    ]
    return result


def _jsonify_projected_record(user_data: dict, record: dict | None, status: int | None = None):
    payload = _project_record_payload(record, _visible_response_fields_for_actor(user_data))
    response = jsonify(payload)
    return (response, status) if status is not None else response


def _jsonify_projected_list(user_data: dict, payload: dict):
    return jsonify(_project_list_payload(payload, _visible_response_fields_for_actor(user_data)))



def _truthy(value):
    return str(value or '').strip().lower() in {'1', 'true', 'yes', 'y', 'si', 'sí', 'on'}


def _bootstrap_admin_username():
    return (os.getenv('BOOTSTRAP_ADMIN_USERNAME') or 'admin1').strip() or 'admin1'


def _bootstrap_enabled():
    return _truthy(os.getenv('BOOTSTRAP_ADMIN_ENABLED', 'true'))


def _actor_is_bootstrap(user_data):
    if not _bootstrap_enabled():
        return False
    return str(user_data.get('username') or '') == _bootstrap_admin_username()


def _bootstrap_only_response():
    # Hide sensitive technical modules from client users and API probing.
    return jsonify({'error_key': 'errors.resource_not_found'}), 404


def _require_bootstrap_actor(user_data):
    if _actor_is_bootstrap(user_data):
        return None
    return _bootstrap_only_response()


@bp_event_log.route('/', methods=['GET'])
@token_required
@require_entity_permission('event_log', 'read')
def list_event_log(user_data):
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    sort = request.args.get('sort')
    filters = {k: v for k, v in request.args.items() if k not in {'page', 'per_page', 'sort'} and k in ALLOWED_FIELDS}
    guard = _require_bootstrap_actor(user_data)
    if guard: return guard
    return jsonify(EventLogService.list(page=page, per_page=per_page, filters=filters, sort=sort))


@bp_event_log.route('/<id_event_log>', methods=['GET'])
@token_required
@require_entity_permission('event_log', 'read')
def get_event_log(user_data, id_event_log):
    guard = _require_bootstrap_actor(user_data)
    if guard: return guard
    return jsonify(EventLogService.get(id_event_log))


@bp_event_log.route('/', methods=['POST'])
@token_required
@require_entity_permission('event_log', 'create')
def create_event_log(user_data):
    guard = _require_bootstrap_actor(user_data)
    if guard: return guard
    return jsonify(EventLogService.create(request.get_json() or {}, user_id=user_data.get('id_user'))), 201


@bp_event_log.route('/<id_event_log>', methods=['PUT'])
@token_required
@require_entity_permission('event_log', 'update')
def update_event_log(user_data, id_event_log):
    guard = _require_bootstrap_actor(user_data)
    if guard: return guard
    return jsonify(EventLogService.update(id_event_log, request.get_json() or {}, user_id=user_data.get('id_user')))


@bp_event_log.route('/<id_event_log>', methods=['DELETE'])
@token_required
@require_entity_permission('event_log', 'delete')
def delete_event_log(user_data, id_event_log):
    guard = _require_bootstrap_actor(user_data)
    if guard: return guard
    return jsonify(EventLogService.delete(id_event_log, user_id=user_data.get('id_user')))
