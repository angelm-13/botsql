from __future__ import annotations
from flask import Blueprint, jsonify, request
from app.services.inventory_status_service import InventoryStatusService
from app.utils.auth import token_required, require_entity_permission
from app.utils.errors import AppError

bp_inventory_status = Blueprint('inventory_status', __name__, url_prefix='/inventory_status')
ALLOWED_FIELDS = ['id_inventory_status', 'inventory_status_code', 'inventory_status_description', 'color', 'entity_scope', 'flow_scope', 'id_department', 'id_subdepartment', 'id_minimum_level', 'is_active', 'is_terminal', 'visible_to_other_departments', 'sort_order', 'created_by', 'creation_date', 'last_update_date', 'deletion_date']

TECHNICAL_RESPONSE_FIELDS = {'id_inventory_status'}
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
            .filter(Field.table_name == 'inventory_status')
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



def _is_inventory_status_superuser(user_data: dict) -> bool:
    return bool(user_data.get('is_superuser') or user_data.get('is_bootstrap_admin'))


def _inventory_status_permission_denied(meta: dict | None = None):
    details = {'entity': 'inventory_status'}
    if meta:
        details.update(meta)
    raise AppError('errors.permission_denied', 403, details)


def _actor_permission_profile(user_data: dict) -> dict | None:
    permission_id = _safe_int_value(user_data.get('id_permission') or user_data.get('permission_id'))
    if not permission_id:
        return None

    from app.models.permission import Permission
    from app.models.session import transaction_context

    with transaction_context() as db_session:
        record = (
            db_session.query(Permission)
            .filter(Permission.id_permission == permission_id)
            .filter(Permission.deletion_date.is_(None))
            .first()
        )
        if not record:
            return None
        return {
            'id_permission': record.id_permission,
            'id_department': record.id_department,
            'id_subdepartment': record.id_subdepartment,
            'id_level': record.id_level,
        }


def _require_inventory_status_manage(user_data: dict, status_payload: dict | None):
    if _is_inventory_status_superuser(user_data):
        return

    actor = _actor_permission_profile(user_data)
    if not actor:
        _inventory_status_permission_denied({'reason': 'missing_permission_profile'})

    status_payload = dict(status_payload or {})
    target_department = _safe_int_value(status_payload.get('id_department'))
    target_subdepartment = _safe_int_value(status_payload.get('id_subdepartment'))
    target_minimum_level = _safe_int_value(status_payload.get('id_minimum_level'))

    if target_department is None or target_minimum_level is None:
        _inventory_status_permission_denied({'reason': 'missing_inventory_status_scope'})

    actor_department = _safe_int_value(actor.get('id_department'))
    actor_subdepartment = _safe_int_value(actor.get('id_subdepartment'))
    actor_level = _safe_int_value(actor.get('id_level'))

    if actor_department != target_department:
        _inventory_status_permission_denied({'reason': 'department_mismatch'})

    if target_subdepartment is not None and actor_subdepartment != target_subdepartment:
        _inventory_status_permission_denied({'reason': 'subdepartment_mismatch'})

    if actor_level is None or actor_level > target_minimum_level:
        _inventory_status_permission_denied({'reason': 'insufficient_level'})



@bp_inventory_status.route('/', methods=['GET'])
@token_required
@require_entity_permission('inventory_status', 'read')
def list_inventory_status(user_data):
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    sort = request.args.get('sort')
    filters = {k: v for k, v in request.args.items() if k not in {'page', 'per_page', 'sort', 'q'} and k in ALLOWED_FIELDS}
    return _jsonify_projected_list(user_data, InventoryStatusService.list(page=page, per_page=per_page, filters=filters, sort=sort, q=request.args.get('q')))


@bp_inventory_status.route('/<id_inventory_status>', methods=['GET'])
@token_required
@require_entity_permission('inventory_status', 'read')
def get_inventory_status(user_data, id_inventory_status):
    return _jsonify_projected_record(user_data, InventoryStatusService.get(id_inventory_status))


@bp_inventory_status.route('/', methods=['POST'])
@token_required
@require_entity_permission('inventory_status', 'create')
def create_inventory_status(user_data):
    payload = _filter_payload_for_actor(request.get_json() or {}, user_data)
    _require_inventory_status_manage(user_data, payload)
    return _jsonify_projected_record(user_data, InventoryStatusService.create(payload, user_id=user_data.get('id_user')), status=201)


@bp_inventory_status.route('/<id_inventory_status>', methods=['PUT'])
@token_required
@require_entity_permission('inventory_status', 'update')
def update_inventory_status(user_data, id_inventory_status):
    payload = _filter_payload_for_actor(request.get_json() or {}, user_data)
    existing = InventoryStatusService.get(id_inventory_status)
    if not existing:
        raise AppError('errors.resource_not_found', 404)
    _require_inventory_status_manage(user_data, existing)
    target = dict(existing)
    target.update(payload)
    _require_inventory_status_manage(user_data, target)
    return _jsonify_projected_record(user_data, InventoryStatusService.update(id_inventory_status, payload, user_id=user_data.get('id_user')))


@bp_inventory_status.route('/<id_inventory_status>', methods=['DELETE'])
@token_required
@require_entity_permission('inventory_status', 'delete')
def delete_inventory_status(user_data, id_inventory_status):
    existing = InventoryStatusService.get(id_inventory_status)
    if not existing:
        raise AppError('errors.resource_not_found', 404)
    _require_inventory_status_manage(user_data, existing)
    return jsonify(InventoryStatusService.delete(id_inventory_status, user_id=user_data.get('id_user')))
