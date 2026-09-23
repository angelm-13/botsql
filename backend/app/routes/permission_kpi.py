from __future__ import annotations
from flask import Blueprint, jsonify, request
from sqlalchemy import select
from app.models.nm_permission_kpi import NmPermissionKpi
from app.models.session import transaction_context
from app.services.nm_permission_kpi_service import NmPermissionKpiService
from app.utils.auth import token_required, require_entity_permission
from app.utils.errors import AppError

bp_permission_kpi = Blueprint('permission_kpi', __name__, url_prefix='/permission_kpi')
ALLOWED_FIELDS = ['id_nm_permission_kpi', 'id_permission', 'id_kpi_definition', 'puede_ver', 'created_by', 'creation_date', 'last_update_date', 'deletion_date']

TECHNICAL_RESPONSE_FIELDS = {'id_nm_permission_kpi'}
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

    visible = set()
    writable = set()
    with transaction_context() as db_session:
        rows = (
            db_session.query(NmFieldPermission, Field)
            .join(Field, NmFieldPermission.id_field == Field.id_field)
            .filter(NmFieldPermission.id_permission == permission_id)
            .filter(NmFieldPermission.deletion_date.is_(None))
            .filter(Field.table_name == 'nm_permission_kpi')
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


@bp_permission_kpi.route('/', methods=['GET'])
@token_required
@require_entity_permission('nm_permission_kpi', 'read')
def list_permission_kpi(user_data):
    """Que KPIs ve un rol hoy -- `?id_permission=<id>` es obligatorio.

    No es el listado paginado generico (`CrudService.list`): esta pantalla
    siempre pide "los KPIs de ESTE rol", nunca la tabla completa, asi que
    filtrar por `id_permission` a mano evita el riesgo de un ILIKE contra una
    columna entera si se hubiera reusado el filtro generico de `CrudService`.
    """
    id_permission = _safe_int_value(request.args.get('id_permission'))
    if id_permission is None:
        raise AppError('errors.required_field', 400, {'field': 'id_permission'})

    visible_fields = _visible_response_fields_for_actor(user_data)
    with transaction_context() as db:
        rows = db.scalars(
            select(NmPermissionKpi).where(
                NmPermissionKpi.id_permission == id_permission,
                NmPermissionKpi.deletion_date.is_(None),
            )
        ).all()
        items = [_project_record_payload(row.serialize(), visible_fields) for row in rows]
    return jsonify({'items': items})


@bp_permission_kpi.route('/', methods=['POST'])
@token_required
@require_entity_permission('nm_permission_kpi', 'create')
def create_permission_kpi(user_data):
    payload = _filter_payload_for_actor(request.get_json() or {}, user_data)
    record = NmPermissionKpiService.create(payload, user_id=user_data.get('id_user'))
    return jsonify(_project_record_payload(record, _visible_response_fields_for_actor(user_data))), 201


@bp_permission_kpi.route('/<id_nm_permission_kpi>', methods=['DELETE'])
@token_required
@require_entity_permission('nm_permission_kpi', 'delete')
def delete_permission_kpi(user_data, id_nm_permission_kpi):
    return jsonify(NmPermissionKpiService.delete(id_nm_permission_kpi, user_id=user_data.get('id_user')))
