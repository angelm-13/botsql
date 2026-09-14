from __future__ import annotations
from flask import Blueprint, jsonify, request
from app.services.level_service import LevelService
from app.utils.auth import token_required, require_entity_permission
from app.utils.errors import AppError
import os


bp_level = Blueprint('level', __name__, url_prefix='/level')
ALLOWED_FIELDS = ['id_level', 'level_description', 'created_by', 'creation_date', 'last_update_date', 'deletion_date']

TECHNICAL_RESPONSE_FIELDS = {'id_level'}
FIELD_READ_BIT = 2
# Escribir un campo exige el bit de alta o el de actualizacion, no el de
# lectura. Sin esta distincion no se podia conceder "ver pero no editar".
FIELD_WRITE_BITS = 1 | 4


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


def _field_sets_for_actor(user_data: dict) -> tuple[set[str], set[str]]:
    """Campos que el actor puede ver y campos que puede escribir."""
    if _actor_has_unrestricted_field_access(user_data):
        return set(ALLOWED_FIELDS), set(ALLOWED_FIELDS)

    permission_id = _safe_int_value(user_data.get('id_permission') or user_data.get('permission_id'))
    if not permission_id:
        return set(TECHNICAL_RESPONSE_FIELDS), set()

    from app.models.field import Field
    from app.models.nm_field_permission import NmFieldPermission
    from app.models.session import transaction_context

    visible = set()
    writable = set()
    with transaction_context() as db_session:
        rows = (
            db_session.query(NmFieldPermission, Field)
            .join(Field, NmFieldPermission.id_field == Field.id_field)
            .filter(NmFieldPermission.id_permission == permission_id)
            .filter(NmFieldPermission.deletion_date.is_(None))
            .filter(Field.table_name == 'level')
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
            if control_type & FIELD_WRITE_BITS:
                writable.add(field_row.field_name)

    # La llave primaria puede viajar en la respuesta para navegacion interna,
    # acciones de fila y rutas REST, aunque el frontend no la pinte si no fue
    # marcada como visible en el gestor.
    return visible | set(TECHNICAL_RESPONSE_FIELDS), writable


def _visible_response_fields_for_actor(user_data: dict) -> set[str]:
    return _field_sets_for_actor(user_data)[0]


def _writable_request_fields_for_actor(user_data: dict) -> set[str]:
    return _field_sets_for_actor(user_data)[1]


def _filter_payload_for_actor(payload: dict, user_data: dict) -> dict:
    payload = dict(payload or {})
    if _actor_has_unrestricted_field_access(user_data):
        return payload
    writable_fields = _writable_request_fields_for_actor(user_data) - set(TECHNICAL_RESPONSE_FIELDS)
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



import os


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


def _hidden_bootstrap_response():
    return jsonify({'error_key': 'errors.resource_not_found'}), 404


def _protected_bootstrap_response():
    return jsonify({'error_key': 'errors.bootstrap_admin_protected'}), 403


def _safe_int_value(value):
    try:
        if value is None or value == '':
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _is_protected_level_id(value):
    return _safe_int_value(value) == 1


def _is_protected_permission_id(value):
    return _safe_int_value(value) == 1


def _is_superuser_level_payload(payload):
    if not payload:
        return False
    if _is_protected_level_id(payload.get('id_level')):
        return True
    description = str(payload.get('level_description') or '').strip().lower()
    return description in {'superusuario', 'superuser', 'bootstrap', 'bootstrap admin', 'bootstrap_admin'}


def _is_protected_permission_payload(payload):
    if not payload:
        return False
    if _is_protected_permission_id(payload.get('id_permission')):
        return True
    if _is_protected_level_id(payload.get('id_level')):
        return True
    description = str(payload.get('permission_description') or '').strip().lower()
    return 'superusuario' in description or 'superuser' in description or 'admin1' in description or 'bootstrap' in description


def _filter_protected_level_list(user_data, result):
    if _actor_is_bootstrap(user_data):
        return result
    items = [item for item in result.get('items', []) if not _is_protected_level_id(item.get('id_level'))]
    removed = len(result.get('items', [])) - len(items)
    if not removed:
        return result
    next_result = dict(result)
    next_result['items'] = items
    next_result['total'] = max(0, int(result.get('total') or 0) - removed)
    per_page_value = int(result.get('per_page') or 20)
    next_result['pages'] = (next_result['total'] + per_page_value - 1) // per_page_value if per_page_value else 0
    return next_result


def _filter_protected_permission_list(user_data, result):
    if _actor_is_bootstrap(user_data):
        return result
    items = [
        item for item in result.get('items', [])
        if not _is_protected_permission_id(item.get('id_permission')) and not _is_protected_level_id(item.get('id_level'))
    ]
    removed = len(result.get('items', [])) - len(items)
    if not removed:
        return result
    next_result = dict(result)
    next_result['items'] = items
    next_result['total'] = max(0, int(result.get('total') or 0) - removed)
    per_page_value = int(result.get('per_page') or 20)
    next_result['pages'] = (next_result['total'] + per_page_value - 1) // per_page_value if per_page_value else 0
    return next_result


def _list_level_protected(user_data, page, per_page, filters, sort, service_cls):
    result = service_cls.list(page=page, per_page=per_page, filters=filters, sort=sort, q=request.args.get('q'))
    return _jsonify_projected_list(user_data, _filter_protected_level_list(user_data, result))


def _get_level_protected(user_data, target_id, service_cls):
    if not _actor_is_bootstrap(user_data) and _is_protected_level_id(target_id):
        return _hidden_bootstrap_response()
    return _jsonify_projected_record(user_data, service_cls.get(target_id))


def _create_level_protected(user_data, payload, service_cls):
    if not _actor_is_bootstrap(user_data) and _is_superuser_level_payload(payload):
        return _protected_bootstrap_response()
    return _jsonify_projected_record(user_data, service_cls.create(payload, user_id=user_data.get('id_user')), status=201)


def _update_level_protected(user_data, target_id, payload, service_cls):
    if not _actor_is_bootstrap(user_data) and (_is_protected_level_id(target_id) or _is_superuser_level_payload(payload)):
        return _protected_bootstrap_response()
    return _jsonify_projected_record(user_data, service_cls.update(target_id, payload, user_id=user_data.get('id_user')))


def _delete_level_protected(user_data, target_id, service_cls):
    if not _actor_is_bootstrap(user_data) and _is_protected_level_id(target_id):
        return _protected_bootstrap_response()
    return jsonify(service_cls.delete(target_id, user_id=user_data.get('id_user')))


def _list_permission_protected(user_data, page, per_page, filters, sort, service_cls):
    result = service_cls.list(page=page, per_page=per_page, filters=filters, sort=sort, q=request.args.get('q'))
    return _jsonify_projected_list(user_data, _filter_protected_permission_list(user_data, result))


def _get_permission_protected(user_data, target_id, service_cls):
    if not _actor_is_bootstrap(user_data) and _is_protected_permission_id(target_id):
        return _hidden_bootstrap_response()
    record = service_cls.get(target_id)
    if not _actor_is_bootstrap(user_data) and record and _is_protected_level_id(record.get('id_level')):
        return _hidden_bootstrap_response()
    return _jsonify_projected_record(user_data, record)


def _create_permission_protected(user_data, payload, service_cls):
    if not _actor_is_bootstrap(user_data) and _is_protected_permission_payload(payload):
        return _protected_bootstrap_response()
    return _jsonify_projected_record(user_data, service_cls.create(payload, user_id=user_data.get('id_user')), status=201)


def _update_permission_protected(user_data, target_id, payload, service_cls):
    if not _actor_is_bootstrap(user_data) and (_is_protected_permission_id(target_id) or _is_protected_permission_payload(payload)):
        return _protected_bootstrap_response()
    return _jsonify_projected_record(user_data, service_cls.update(target_id, payload, user_id=user_data.get('id_user')))


def _delete_permission_protected(user_data, target_id, service_cls):
    if not _actor_is_bootstrap(user_data) and _is_protected_permission_id(target_id):
        return _protected_bootstrap_response()
    return jsonify(service_cls.delete(target_id, user_id=user_data.get('id_user')))


@bp_level.route('/', methods=['GET'])
@token_required
@require_entity_permission('level', 'read')
def list_level(user_data):
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    sort = request.args.get('sort')
    filters = {k: v for k, v in request.args.items() if k not in {'page', 'per_page', 'sort', 'q'} and k in ALLOWED_FIELDS}
    return _list_level_protected(user_data, page, per_page, filters, sort, LevelService)


@bp_level.route('/<id_level>', methods=['GET'])
@token_required
@require_entity_permission('level', 'read')
def get_level(user_data, id_level):
    return _get_level_protected(user_data, id_level, LevelService)


@bp_level.route('/', methods=['POST'])
@token_required
@require_entity_permission('level', 'create')
def create_level(user_data):
    payload = _filter_payload_for_actor(request.get_json() or {}, user_data)
    return _create_level_protected(user_data, payload, LevelService)


@bp_level.route('/<id_level>', methods=['PUT'])
@token_required
@require_entity_permission('level', 'update')
def update_level(user_data, id_level):
    payload = _filter_payload_for_actor(request.get_json() or {}, user_data)
    return _update_level_protected(user_data, id_level, payload, LevelService)


@bp_level.route('/<id_level>', methods=['DELETE'])
@token_required
@require_entity_permission('level', 'delete')
def delete_level(user_data, id_level):
    return _delete_level_protected(user_data, id_level, LevelService)
