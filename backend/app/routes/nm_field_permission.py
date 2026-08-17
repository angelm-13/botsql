from __future__ import annotations
from flask import Blueprint, jsonify, request
from app.services.nm_field_permission_service import NmFieldPermissionService
from app.utils.auth import token_required, require_entity_permission
from app.utils.errors import AppError

bp_nm_field_permission = Blueprint('nm_field_permission', __name__, url_prefix='/nm_field_permission')
ALLOWED_FIELDS = ['id_nm_field_permission', 'id_field', 'id_permission', 'control_type', 'created_by', 'creation_date', 'last_update_date', 'deletion_date']

TECHNICAL_RESPONSE_FIELDS = {'id_nm_field_permission'}
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
            .filter(Field.table_name == 'nm_field_permission')
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



@bp_nm_field_permission.route('/', methods=['GET'])
@token_required
@require_entity_permission('nm_field_permission', 'read')
def list_nm_field_permission(user_data):
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    sort = request.args.get('sort')
    filters = {k: v for k, v in request.args.items() if k not in {'page', 'per_page', 'sort'} and k in ALLOWED_FIELDS}
    return _jsonify_projected_list(user_data, NmFieldPermissionService.list(page=page, per_page=per_page, filters=filters, sort=sort))


@bp_nm_field_permission.route('/<id_nm_field_permission>', methods=['GET'])
@token_required
@require_entity_permission('nm_field_permission', 'read')
def get_nm_field_permission(user_data, id_nm_field_permission):
    return _jsonify_projected_record(user_data, NmFieldPermissionService.get(id_nm_field_permission))


@bp_nm_field_permission.route('/', methods=['POST'])
@token_required
@require_entity_permission('nm_field_permission', 'create')
def create_nm_field_permission(user_data):
    payload = _filter_payload_for_actor(request.get_json() or {}, user_data)
    return _jsonify_projected_record(user_data, NmFieldPermissionService.create(payload, user_id=user_data.get('id_user')), status=201)


@bp_nm_field_permission.route('/<id_nm_field_permission>', methods=['PUT'])
@token_required
@require_entity_permission('nm_field_permission', 'update')
def update_nm_field_permission(user_data, id_nm_field_permission):
    payload = _filter_payload_for_actor(request.get_json() or {}, user_data)
    return _jsonify_projected_record(user_data, NmFieldPermissionService.update(id_nm_field_permission, payload, user_id=user_data.get('id_user')))


@bp_nm_field_permission.route('/<id_nm_field_permission>', methods=['DELETE'])
@token_required
@require_entity_permission('nm_field_permission', 'delete')
def delete_nm_field_permission(user_data, id_nm_field_permission):
    return jsonify(NmFieldPermissionService.delete(id_nm_field_permission, user_id=user_data.get('id_user')))
