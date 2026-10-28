from __future__ import annotations
from datetime import datetime
import re
from flask import Blueprint, jsonify, request
import bcrypt
from app.services.user_service import UserService
from app.services.related_records import delete_has_related_records_error
from app.utils.auth import token_required, require_entity_permission
from app.utils.errors import AppError
import os
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, StatementError
from app.models.session import transaction_context
from app.utils.field_access import COLUMNAS_DE_AUDITORIA
from app.routes.permission import _is_protected_permission_id
from app.utils.user_access import can_manage_user, changes_own_role


bp_user = Blueprint('user', __name__, url_prefix='/user')

# La capacidad que designa a quien puede ser responsable de un vale de material.
RESPONSABLE_DE_VALE = 'warehouse_voucher_holder'
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
    return visible | set(TECHNICAL_RESPONSE_FIELDS) | COLUMNAS_DE_AUDITORIA, writable


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


def _get_user_row(session, target_user_id):
    return session.execute(
        text('SELECT id_user, username, user_type, id_permission FROM "user" WHERE id_user = :id_user'),
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
    """Si el actor puede editar o borrar a este usuario.

    Que pueda gestionar usuarios en general lo decide el Gestor (la ruta ya lo
    exige); aqui solo rigen las protecciones de `app/utils/user_access.py`,
    ninguna por `user_type`.
    """
    if _actor_is_bootstrap(user_data):
        return True
    if not target:
        return False
    return can_manage_user(user_data, target.get('id_permission'),
                           actor_is_bootstrap=False, target_is_bootstrap=_row_is_bootstrap(target))


def _can_create_user_payload(user_data, payload):
    if _actor_is_bootstrap(user_data):
        return True
    # Nadie crea una cuenta que se haga pasar por el superusuario. Asignar el
    # rol Administrator lo cubre `_payload_assigns_protected_role`; fuera de eso
    # quien puede dar de alta usuarios lo decide el Gestor.
    target_type = _normalize_user_type((payload or {}).get('user_type')) or 'employee'
    return target_type not in {'superuser', 'bootstrap', 'bootstrap_admin'}


def _payload_attempts_forbidden_bootstrap_identity(payload):
    if not payload:
        return False
    forbidden_flags = {'is_superuser', 'is_bootstrap_admin', 'bootstrap', 'bootstrap_admin'}
    if any(_truthy(payload.get(key)) for key in forbidden_flags):
        return True
    username = str(payload.get('username') or '').strip()
    return _bootstrap_enabled() and username == _bootstrap_admin_username()


def _payload_assigns_protected_role(user_data, payload, target=None):
    """Quien no es el bootstrap no puede asignar el rol bootstrap a nadie.

    El selector ya no lo ofrece (`/permission/options`), pero esconderlo en la
    pantalla no basta: la API aceptaba cualquier `id_permission`. Conservar el
    rol que el usuario ya tenia no cuenta (editar otros campos de un usuario
    que ya lo tiene reenvia el mismo valor).
    """
    if _actor_is_bootstrap(user_data) or not payload or 'id_permission' not in payload:
        return False
    if not _is_protected_permission_id(payload.get('id_permission')):
        return False
    return not _is_protected_permission_id((target or {}).get('id_permission'))


def _payload_elevates_beyond_actor(user_data, target, payload):
    if _actor_is_bootstrap(user_data):
        return False
    if _payload_attempts_forbidden_bootstrap_identity(payload):
        return True
    # Autoescalada: nadie se cambia a si mismo el rol. `user_type` ya no cuenta:
    # describe la cuenta, no da autoridad.
    return changes_own_role(user_data, target, payload)


def _list_users_protected(user_data, page, per_page, filters, sort, service_cls, search_fields=None):
    result = service_cls.list(page=page, per_page=per_page, filters=filters, sort=sort, q=request.args.get('q'), search_fields=search_fields)
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
    if _payload_assigns_protected_role(user_data, payload):
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
        if _payload_assigns_protected_role(user_data, payload, target):
            return _protected_bootstrap_response()
    duplicate = _validate_user_unique_fields(payload, exclude_user_id=target_user_id)
    if duplicate:
        return duplicate
    return _jsonify_projected_record(user_data, service_cls.update(target_user_id, payload, user_id=user_data.get('id_user')))


def _raise_user_delete_constraint_error(error, target_user_id=None):
    detail = str(error.orig) if getattr(error, 'orig', None) else str(error)
    normalized = detail.lower()
    if 'violates foreign key constraint' in normalized and 'is still referenced from table' in normalized:
        raise delete_has_related_records_error('user', 'user', target_user_id)
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
        _raise_user_delete_constraint_error(error, target_user_id)


@bp_user.route('/options', methods=['GET'])
@token_required
def list_user_options(user_data):
    """Solo id+nombre, para selectores como "Responsable" en un vale de
    almacen o el lider de un proyecto.

    Sin permiso de entidad de por medio a proposito: cualquier usuario
    autenticado puede necesitar asignarle algo a un companero (un vale, un
    proyecto) sin tener acceso al catalogo de RH completo -- solo id+nombre,
    nada de puesto/salario/RFC/etc.

    `?para=vale_responsable` deja solo a quienes el Gestor de roles y permisos
    designo como posibles responsables de un vale de material.
    """
    capacidad = RESPONSABLE_DE_VALE if request.args.get("para") == "vale_responsable" else None
    return jsonify(UserService.options(capability=capacidad))


@bp_user.route('/', methods=['GET'])
@token_required
@require_entity_permission('user', 'read')
def list_user(user_data):
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    sort = request.args.get('sort')
    visible = _visible_response_fields_for_actor(user_data)
    filters = {k: v for k, v in request.args.items() if k not in {'page', 'per_page', 'sort', 'q'} and k in visible and k in ALLOWED_FIELDS}
    if sort and sort.lstrip('-') not in visible:
        sort = None
    return _list_users_protected(user_data, page, per_page, filters, sort, UserService, visible)


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


@bp_user.route('/me/password', methods=['POST'])
@token_required
def change_own_password(user_data):
    """Cualquier usuario autenticado cambia SU PROPIA contrasena.

    Sin `require_entity_permission` a proposito, igual que `/user/options`:
    la fila que se toca es siempre la del propio actor (`user_data['id_user']`),
    nunca una que llegue por parametro, asi que el permiso de entidad de
    `user` -que hoy solo tiene Administrator- no aplica aqui y no hace
    falta.

    No existia ningun camino para esto antes: `password` esta fuera de
    `ALLOWED_FIELDS` del CRUD generico de usuarios de este archivo, asi que
    ni siquiera Administrator podia cambiarla desde la app -- solo se fija
    al sembrar o crear la cuenta. La cuenta de arranque (bootstrap) tambien
    puede usar esta ruta: es la unica forma de cambiar SU password, ya que
    esta fuera del CRUD por completo.
    """
    payload = request.get_json(silent=True) or {}
    current_password = str(payload.get('current_password') or '')
    new_password = str(payload.get('new_password') or '')
    if len(new_password) < 8 or not re.search(r'[A-Za-z]', new_password) or not re.search(r'[0-9]', new_password):
        raise AppError('errors.validation_failed', 400, {'field': 'new_password'})

    with transaction_context() as session:
        user = session.get(UserService.model, user_data.get('id_user'))
        if user is None:
            raise AppError('errors.resource_not_found', 404)
        stored = getattr(user, 'password', None) or ''
        if not stored or not bcrypt.checkpw(current_password.encode('utf-8'), stored.encode('utf-8')):
            # 400 y no 401: un 401 en este frontend (ver api/client.js) borra
            # el token y manda a /login -- correcto para una sesion invalida,
            # pero esto no es eso, es una contrasena actual mal escrita en un
            # formulario, con la sesion todavia perfectamente valida.
            raise AppError('errors.auth_invalid_credentials', 400)
        user.password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        user.last_update_date = datetime.utcnow()
        try:
            from app.models import EventLog
            session.add(EventLog(
                table_name='user', field_name='password', action='update',
                event_detail='self_service_password_change',
                before_value={}, after_value={},
                created_by=user_data.get('id_user') or 1,
            ))
        except Exception:
            pass
        session.flush()
    return jsonify({'message_key': 'success.password_changed'})
