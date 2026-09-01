from __future__ import annotations
from flask import Blueprint, jsonify, request
from app.services.user_service import UserService
from app.utils.auth import token_required, require_entity_permission
from app.utils.errors import AppError
import os
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, StatementError
from app.models.session import transaction_context


bp_user = Blueprint('user', __name__, url_prefix='/user')
ALLOWED_FIELDS = ['id_user', 'created_by', 'creation_date', 'date_born', 'date_start', 'deletion_date', 'email', 'first_name', 'id_permission', 'full_name', 'id_proyect', 'last_name_father', 'last_name_mother', 'last_update_date', 'national_id', 'principal_phone', 'secundary_phone', 'ssn', 'supervisor', 'base_salary', 'hire_date', 'id_status', 'tax_id', 'title', 'user_type', 'username', 'supervisor', 'puesto', 'is_employee', 'accepts_marketing']

TECHNICAL_RESPONSE_FIELDS = {'id_user'}
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
            .filter(Field.table_name == 'user')
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


def _row_is_bootstrap(row):
    if not row or not _bootstrap_enabled():
        return False
    return str(row.get('username') or '') == _bootstrap_admin_username()


def _normalize_user_type(value):
    return str(value or '').strip().lower()


def _company_admin_types():
    raw = os.getenv('COMPANY_ADMIN_USER_TYPES', 'admin')
    return {item.strip().lower() for item in raw.split(',') if item.strip()} or {'admin'}


def _user_hierarchy_rank_from_type(user_type):
    # Flexible default hierarchy. It can be extended later with USER_HIERARCHY_RANKS,
    # for example: USER_HIERARCHY_RANKS="admin:80,manager:60,employee:40".
    # If level grows a formal hierarchy field in a later phase, only this central
    # function should be adapted to read that rank.
    ranks = {'admin': 80, 'client': 50, 'supplier': 50, 'employee': 40, 'user': 20, '': 10}
    raw = os.getenv('USER_HIERARCHY_RANKS', '')
    for part in raw.split(','):
        if ':' not in part:
            continue
        key, value = part.split(':', 1)
        try:
            ranks[key.strip().lower()] = int(value.strip())
        except (TypeError, ValueError):
            continue
    return ranks.get(_normalize_user_type(user_type), ranks.get('', 10))


def _actor_is_company_admin(user_data):
    return _normalize_user_type(user_data.get('user_type')) in _company_admin_types()


def _get_user_row(session, target_user_id):
    return session.execute(
        text('SELECT id_user, username, user_type FROM "user" WHERE id_user = :id_user'),
        {'id_user': target_user_id},
    ).mappings().first()


def _hidden_bootstrap_response():
    # Return 404 to avoid confirming the existence of the internal audit user.
    return jsonify({'error_key': 'errors.resource_not_found'}), 404


def _protected_bootstrap_response():
    return jsonify({'error_key': 'errors.bootstrap_admin_protected'}), 403


def _hierarchy_denied_response():
    return jsonify({'error_key': 'errors.user_hierarchy_denied'}), 403


def _create_hierarchy_denied_response():
    return jsonify({'error_key': 'errors.cannot_create_higher_user'}), 403


def _can_manage_user_row(user_data, target):
    if _actor_is_bootstrap(user_data):
        return True
    if not target:
        return False
    if _row_is_bootstrap(target):
        return False
    # The company admin is the operational owner. It may manage other normal
    # admins and lower users, but never the unique bootstrap/superuser.
    if _actor_is_company_admin(user_data):
        return True
    actor_rank = _user_hierarchy_rank_from_type(user_data.get('user_type'))
    target_rank = _user_hierarchy_rank_from_type(target.get('user_type'))
    return actor_rank > target_rank


def _can_create_user_payload(user_data, payload):
    if _actor_is_bootstrap(user_data):
        return True
    target_type = _normalize_user_type((payload or {}).get('user_type')) or 'employee'
    if target_type in {'superuser', 'bootstrap', 'bootstrap_admin'}:
        return False
    # Company admins may create other normal admins and lower users because they
    # administer the client installation after delivery.
    if _actor_is_company_admin(user_data):
        return True
    actor_rank = _user_hierarchy_rank_from_type(user_data.get('user_type'))
    target_rank = _user_hierarchy_rank_from_type(target_type)
    return actor_rank > target_rank


def _payload_attempts_forbidden_bootstrap_identity(payload):
    if not payload:
        return False
    forbidden_flags = {'is_superuser', 'is_bootstrap_admin', 'bootstrap', 'bootstrap_admin'}
    if any(_truthy(payload.get(key)) for key in forbidden_flags):
        return True
    username = str(payload.get('username') or '').strip()
    return _bootstrap_enabled() and username == _bootstrap_admin_username()


def _payload_elevates_beyond_actor(user_data, target, payload):
    if _actor_is_bootstrap(user_data):
        return False
    if _payload_attempts_forbidden_bootstrap_identity(payload):
        return True
    if not payload or 'user_type' not in payload:
        return False
    desired_type = _normalize_user_type(payload.get('user_type'))
    current_type = _normalize_user_type((target or {}).get('user_type'))
    if desired_type == current_type:
        return False
    if _actor_is_company_admin(user_data):
        return False
    actor_rank = _user_hierarchy_rank_from_type(user_data.get('user_type'))
    desired_rank = _user_hierarchy_rank_from_type(desired_type)
    return desired_rank >= actor_rank


def _list_users_protected(user_data, page, per_page, filters, sort, service_cls):
    result = service_cls.list(page=page, per_page=per_page, filters=filters, sort=sort)
    original_items = list(result.get('items', []) or [])
    items = [
        item for item in original_items
        if str(item.get('user_type') or '').strip().lower() != 'web_shopper'
    ]

    if not _actor_is_bootstrap(user_data):
        bootstrap_username = _bootstrap_admin_username()
        items = [
            item for item in items
            if str(item.get('username') or '') != bootstrap_username
        ]

    removed = len(original_items) - len(items)
    if removed:
        result = dict(result)
        result['items'] = items
        result['total'] = max(0, int(result.get('total') or 0) - removed)
        per_page_value = int(result.get('per_page') or per_page or 20)
        result['pages'] = (result['total'] + per_page_value - 1) // per_page_value if per_page_value else 0
    return _jsonify_projected_list(user_data, result)


def _get_user_protected(user_data, target_user_id, service_cls):
    if _actor_is_bootstrap(user_data):
        return _jsonify_projected_record(user_data, service_cls.get(target_user_id))
    with transaction_context() as session:
        target = _get_user_row(session, target_user_id)
        if _row_is_bootstrap(target):
            return _hidden_bootstrap_response()
    return _jsonify_projected_record(user_data, service_cls.get(target_user_id))


def _duplicate_username_response():
    return jsonify({'error_key': 'errors.username_already_exists'}), 409


def _duplicate_email_response():
    return jsonify({'error_key': 'errors.email_already_exists'}), 409


def _normalize_unique_value(value):
    return str(value or '').strip().lower()


def _user_unique_conflict(session, *, field_name, value, exclude_user_id=None):
    normalized = _normalize_unique_value(value)
    if not normalized:
        return False
    if field_name not in {'username', 'email'}:
        return False
    query = (
        'SELECT id_user FROM "user" '
        f'WHERE lower({field_name}) = :value '
        'AND (:exclude_user_id IS NULL OR id_user <> :exclude_user_id) '
        'LIMIT 1'
    )
    row = session.execute(
        text(query),
        {'value': normalized, 'exclude_user_id': exclude_user_id},
    ).mappings().first()
    return row is not None


def _validate_user_unique_fields(payload, *, exclude_user_id=None):
    if not payload:
        return None
    with transaction_context() as session:
        if 'username' in payload and _user_unique_conflict(session, field_name='username', value=payload.get('username'), exclude_user_id=exclude_user_id):
            return _duplicate_username_response()
        if 'email' in payload and _user_unique_conflict(session, field_name='email', value=payload.get('email'), exclude_user_id=exclude_user_id):
            return _duplicate_email_response()
    return None


def _create_user_protected(user_data, payload, service_cls):
    duplicate = _validate_user_unique_fields(payload)
    if duplicate:
        return duplicate
    if _payload_attempts_forbidden_bootstrap_identity(payload):
        return _protected_bootstrap_response()
    if not _can_create_user_payload(user_data, payload):
        return _create_hierarchy_denied_response()
    return _jsonify_projected_record(user_data, service_cls.create(payload, user_id=user_data.get('id_user')), status=201)


def _update_user_protected(user_data, target_user_id, payload, service_cls):
    with transaction_context() as session:
        target = _get_user_row(session, target_user_id)
        if _row_is_bootstrap(target) and not _actor_is_bootstrap(user_data):
            return _hidden_bootstrap_response()
        if not _can_manage_user_row(user_data, target):
            return _hierarchy_denied_response()
        if _payload_elevates_beyond_actor(user_data, target, payload):
            return _create_hierarchy_denied_response()
    duplicate = _validate_user_unique_fields(payload, exclude_user_id=target_user_id)
    if duplicate:
        return duplicate
    return _jsonify_projected_record(user_data, service_cls.update(target_user_id, payload, user_id=user_data.get('id_user')))


def _raise_user_delete_constraint_error(error):
    detail = str(error.orig) if getattr(error, 'orig', None) else str(error)
    normalized = detail.lower()
    if 'violates foreign key constraint' in normalized and 'is still referenced from table' in normalized:
        raise AppError(
            'errors.delete_has_related_records',
            status_code=409,
            meta={'entity': 'user', 'action': 'delete'},
        )
    raise AppError('errors.database_constraint', status_code=400, meta={'detail': detail})


def _delete_user_or_retire_bootstrap(user_data, target_user_id, service_cls):
    try:
        with transaction_context() as session:
            target = _get_user_row(session, target_user_id)
            if str(target_user_id) == str(user_data.get('id_user') or ''):
                return jsonify({'error_key': 'errors.cannot_delete_current_user'}), 403
            if _row_is_bootstrap(target):
                # New policy: bootstrap admin is an internal audit/support user.
                # It must stay in the system, hidden from client users, and cannot be deleted from the app.
                return _protected_bootstrap_response()
            if not _can_manage_user_row(user_data, target):
                return _hierarchy_denied_response()
            item = session.get(service_cls.model, target_user_id)
            if not item:
                raise AppError('errors.resource_not_found', status_code=404)
            # User MFA is a technical dependent record. Remove it in the same
            # transaction before deleting regular users so admins can remove
            # users that already completed MFA without violating FK constraints.
            before = item.serialize()
            session.execute(text('DELETE FROM user_mfa WHERE id_user = :id_user'), {'id_user': target_user_id})
            session.delete(item)
            try:
                from app.models import EventLog
                session.add(EventLog(
                    table_name='user',
                    field_name='*',
                    action='delete',
                    before_value=before,
                    after_value={},
                    created_by=user_data.get('id_user') or 1,
                ))
            except Exception:
                pass
            session.flush()
            return jsonify({'message_key': 'success.deleted'})
    except AppError:
        raise
    except (IntegrityError, StatementError) as error:
        _raise_user_delete_constraint_error(error)


@bp_user.route('/', methods=['GET'])
@token_required
@require_entity_permission('user', 'read')
def list_user(user_data):
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    sort = request.args.get('sort')
    filters = {k: v for k, v in request.args.items() if k not in {'page', 'per_page', 'sort'} and k in ALLOWED_FIELDS}
    return _list_users_protected(user_data, page, per_page, filters, sort, UserService)


@bp_user.route('/<id_user>', methods=['GET'])
@token_required
@require_entity_permission('user', 'read')
def get_user(user_data, id_user):
    record = UserService.get(id_user)
    if record and str(record.get('user_type') or '').strip().lower() == 'web_shopper':
        return jsonify({'error_key': 'errors.resource_not_found'}), 404
    return _get_user_protected(user_data, id_user, UserService)


@bp_user.route('/', methods=['POST'])
@token_required
@require_entity_permission('user', 'create')
def create_user(user_data):
    payload = _filter_payload_for_actor(request.get_json() or {}, user_data)
    if str(payload.get('user_type') or '').strip().lower() == 'web_shopper':
        return jsonify({'error_key': 'errors.forbidden'}), 403
    return _create_user_protected(user_data, payload, UserService)


@bp_user.route('/<id_user>', methods=['PUT'])
@token_required
@require_entity_permission('user', 'update')
def update_user(user_data, id_user):
    existing = UserService.get(id_user)
    if existing and str(existing.get('user_type') or '').strip().lower() == 'web_shopper':
        return jsonify({'error_key': 'errors.resource_not_found'}), 404
    payload = _filter_payload_for_actor(request.get_json() or {}, user_data)
    return _update_user_protected(user_data, id_user, payload, UserService)


@bp_user.route('/<id_user>', methods=['DELETE'])
@token_required
@require_entity_permission('user', 'delete')
def delete_user(user_data, id_user):
    existing = UserService.get(id_user)
    if existing and str(existing.get('user_type') or '').strip().lower() == 'web_shopper':
        return jsonify({'error_key': 'errors.resource_not_found'}), 404
    return _delete_user_or_retire_bootstrap(user_data, id_user, UserService)
