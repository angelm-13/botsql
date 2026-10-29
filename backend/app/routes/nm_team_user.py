from __future__ import annotations
from flask import Blueprint, jsonify, request
from app.services.nm_team_user_service import NmTeamUserService
from app.utils.auth import token_required, require_entity_permission

bp_nm_team_user = Blueprint('nm_team_user', __name__, url_prefix='/nm_team_user')
ALLOWED_FIELDS = ['id_nm_team_user', 'id_team', 'id_user', 'created_by', 'creation_date', 'last_update_date', 'deletion_date']

# Tabla puente de dos columnas de negocio: el acceso lo decide el permiso de `team` (se administra desde
# esa pantalla, igual que `nm_field_permission` desde el gestor de permisos) y no hay filtro de campos propio.
# Lo que se puede escribir es solo la pareja equipo-persona; cualquier otro campo del cuerpo se ignora.
WRITABLE_FIELDS = {'id_team', 'id_user'}


def _field_sets_for_actor(user_data: dict) -> tuple[set[str], set[str]]:
    """Campos que el actor puede ver y campos que puede escribir: los mismos para todo el que pase el guardia."""
    return set(ALLOWED_FIELDS), set(WRITABLE_FIELDS)


def _visible_response_fields_for_actor(user_data: dict) -> set[str]:
    return _field_sets_for_actor(user_data)[0]


def _writable_request_fields_for_actor(user_data: dict) -> set[str]:
    return _field_sets_for_actor(user_data)[1]


def _filter_payload_for_actor(payload: dict, user_data: dict) -> dict:
    payload = dict(payload or {})
    return {key: value for key, value in payload.items() if key in _writable_request_fields_for_actor(user_data)}


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


@bp_nm_team_user.route('/', methods=['GET'])
@token_required
@require_entity_permission('team', 'read')
def list_nm_team_user(user_data):
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    sort = request.args.get('sort')
    filters = {k: v for k, v in request.args.items() if k not in {'page', 'per_page', 'sort', 'q'} and k in ALLOWED_FIELDS}
    return _jsonify_projected_list(user_data, NmTeamUserService.list(page=page, per_page=per_page, filters=filters, sort=sort, q=request.args.get('q')))


@bp_nm_team_user.route('/<id_nm_team_user>', methods=['GET'])
@token_required
@require_entity_permission('team', 'read')
def get_nm_team_user(user_data, id_nm_team_user):
    return _jsonify_projected_record(user_data, NmTeamUserService.get(id_nm_team_user))


@bp_nm_team_user.route('/', methods=['POST'])
@token_required
@require_entity_permission('team', 'create')
def create_nm_team_user(user_data):
    payload = _filter_payload_for_actor(request.get_json() or {}, user_data)
    return _jsonify_projected_record(user_data, NmTeamUserService.create(payload, user_id=user_data.get('id_user')), status=201)


@bp_nm_team_user.route('/<id_nm_team_user>', methods=['PUT'])
@token_required
@require_entity_permission('team', 'update')
def update_nm_team_user(user_data, id_nm_team_user):
    payload = _filter_payload_for_actor(request.get_json() or {}, user_data)
    return _jsonify_projected_record(user_data, NmTeamUserService.update(id_nm_team_user, payload, user_id=user_data.get('id_user')))


@bp_nm_team_user.route('/<id_nm_team_user>', methods=['DELETE'])
@token_required
@require_entity_permission('team', 'delete')
def delete_nm_team_user(user_data, id_nm_team_user):
    return jsonify(NmTeamUserService.delete(id_nm_team_user, user_id=user_data.get('id_user')))
