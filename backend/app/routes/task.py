from __future__ import annotations
from flask import Blueprint, jsonify, request
from sqlalchemy import func
from app.models.session import transaction_context
from app.models.task import Task
from app.models.task_note import TaskNote
from app.services.project_management_service import require_project_access, require_project_taken_by_actor, require_task_access, visible_project_ids
from app.services.task_service import TaskService, add_task_note, transition_task
from app.utils.auth import token_required, require_entity_permission
from app.utils.errors import AppError
from app.utils.field_access import COLUMNAS_DE_AUDITORIA

bp_task = Blueprint('task', __name__, url_prefix='/task')
ALLOWED_FIELDS = ['id_task', 'task_code', 'start_date', 'duration', 'type', 'owner', 'dependency', 'validation', 'task_description', 'estimated_effort', 'task_status', 'fase', 'priority', 'title', 'id_proyect', 'created_by', 'creation_date', 'last_update_date', 'deletion_date']

TECHNICAL_RESPONSE_FIELDS = {'id_task'}
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
            .filter(Field.table_name == 'task')
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



@bp_task.route('/', methods=['GET'])
@token_required
@require_entity_permission('task', 'read')
def list_task(user_data):
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    sort = request.args.get('sort')
    filters = {k: v for k, v in request.args.items() if k not in {'page', 'per_page', 'sort', 'q'} and k in ALLOWED_FIELDS}
    project_ids = visible_project_ids(user_data)
    if project_ids is None:
        return _jsonify_projected_list(user_data, TaskService.list(page=page, per_page=per_page, filters=filters, sort=sort, q=request.args.get('q')))
    with transaction_context() as db:
        query = db.query(Task).filter(Task.deletion_date.is_(None), Task.id_proyect.in_(project_ids))
        for key, value in filters.items():
            if hasattr(Task, key) and value not in (None, ''):
                query = query.filter(getattr(Task, key) == value)
        total = query.with_entities(func.count()).scalar() or 0
        items = query.order_by(Task.id_task).offset((page - 1) * per_page).limit(per_page).all()
        payload = {'items': [item.serialize() for item in items], 'total': total, 'page': page, 'per_page': per_page, 'pages': (total + per_page - 1) // per_page}
    return _jsonify_projected_list(user_data, payload)


@bp_task.route('/<id_task>', methods=['GET'])
@token_required
@require_entity_permission('task', 'read')
def get_task(user_data, id_task):
    require_task_access(id_task, user_data)
    return _jsonify_projected_record(user_data, TaskService.get(id_task))


@bp_task.route('/', methods=['POST'])
@token_required
@require_entity_permission('task', 'create')
def create_task(user_data):
    payload = _filter_payload_for_actor(request.get_json() or {}, user_data)
    require_project_access(payload.get('id_proyect'), user_data)
    # Del proyecto al que se asigno, no de cualquiera visible del taller
    # (pedido de negocio explicito, 2026-09-28): ver
    # `require_project_taken_by_actor`.
    require_project_taken_by_actor(payload.get('id_proyect'), user_data)
    # El responsable es siempre quien crea la tarea -- Jefe de taller es el
    # unico que da de alta, igual que `leader` en proyectos (ver
    # project_management_service.create_project). El formulario reducido ya
    # no captura owner/dependency/validation, y las dos ultimas son NOT NULL
    # en la base sin uso real como distincion de usuarios (ver docstring de
    # task_service.py), asi que se completan aqui con un valor inerte.
    actor_id = user_data.get('id_user')
    payload['owner'] = actor_id
    payload.setdefault('dependency', 0)
    payload.setdefault('validation', actor_id)
    return _jsonify_projected_record(user_data, TaskService.create(payload, user_id=actor_id), status=201)


@bp_task.route('/<id_task>', methods=['PUT'])
@token_required
@require_entity_permission('task', 'update')
def update_task(user_data, id_task):
    payload = _filter_payload_for_actor(request.get_json() or {}, user_data)
    require_task_access(id_task, user_data)
    if payload.get('id_proyect') is not None:
        require_project_access(payload.get('id_proyect'), user_data)
    return _jsonify_projected_record(user_data, TaskService.update(id_task, payload, user_id=user_data.get('id_user')))


@bp_task.route('/<id_task>/transition', methods=['POST'])
@token_required
@require_entity_permission('task', 'update')
def transition_task_status(user_data, id_task):
    """Cambio de estatus guiado, como en `/proyect/<id>/transition`."""
    return _jsonify_projected_record(user_data, transition_task(id_task, request.get_json() or {}, user_data))


@bp_task.route('/<id_task>/notes', methods=['GET'])
@token_required
@require_entity_permission('task_note', 'read')
def list_task_notes(user_data, id_task):
    """La bitacora de UNA tarea, que es como se lee.

    `/task_note/?id_task=N` ya sabia filtrar, pero obligaba a la pantalla a
    saber el nombre de la columna del padre. Aqui la relacion la pone la ruta,
    igual que en `/proyect/<id>`.
    """
    require_task_access(id_task, user_data)
    with transaction_context() as db:
        rows = (
            db.query(TaskNote)
            .filter(TaskNote.id_task == int(id_task), TaskNote.deletion_date.is_(None))
            .order_by(TaskNote.creation_date.asc(), TaskNote.id_task_note.asc())
            .all()
        )
        return jsonify({'items': [row.serialize() for row in rows], 'total': len(rows)})


@bp_task.route('/<id_task>/notes', methods=['POST'])
@token_required
@require_entity_permission('task_note', 'create')
def create_task_note_for_task(user_data, id_task):
    return jsonify(add_task_note(id_task, request.get_json() or {}, user_data)), 201


@bp_task.route('/<id_task>', methods=['DELETE'])
@token_required
@require_entity_permission('task', 'delete')
def delete_task(user_data, id_task):
    require_task_access(id_task, user_data)
    return jsonify(TaskService.delete(id_task, user_id=user_data.get('id_user')))
