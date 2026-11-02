from __future__ import annotations
from flask import Blueprint, current_app, jsonify, request, send_file
from app.services.employee_leave_service import EmployeeLeaveService
from app.utils.auth import token_required, require_entity_permission
from app.utils.errors import AppError
from app.utils.field_access import COLUMNAS_DE_AUDITORIA

bp_employee_leave = Blueprint('employee_leave', __name__, url_prefix='/employee_leave')
ALLOWED_FIELDS = ['id_employee_leave', 'id_user', 'leave_type', 'start_date', 'end_date', 'notes', 'disability_type', 'leave_status', 'requested_by', 'reviewed_by', 'reviewed_at', 'review_note', 'created_by', 'creation_date', 'last_update_date', 'deletion_date']

TECHNICAL_RESPONSE_FIELDS = {'id_employee_leave'}
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
            .filter(Field.table_name == 'employee_leave')
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



@bp_employee_leave.route('/', methods=['GET'])
@token_required
@require_entity_permission('employee_leave', 'read')
def list_employee_leave(user_data):
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    sort = request.args.get('sort')
    filters = {k: v for k, v in request.args.items() if k not in {'page', 'per_page', 'sort', 'q'} and k in ALLOWED_FIELDS}
    return _jsonify_projected_list(user_data, EmployeeLeaveService.list(page=page, per_page=per_page, filters=filters, sort=sort, q=request.args.get('q')))


@bp_employee_leave.route('/<id_employee_leave>', methods=['GET'])
@token_required
@require_entity_permission('employee_leave', 'read')
def get_employee_leave(user_data, id_employee_leave):
    return _jsonify_projected_record(user_data, EmployeeLeaveService.get(id_employee_leave))


@bp_employee_leave.route('/', methods=['POST'])
@token_required
@require_entity_permission('employee_leave', 'create')
def create_employee_leave(user_data):
    payload = _filter_payload_for_actor(request.get_json() or {}, user_data)
    return _jsonify_projected_record(user_data, EmployeeLeaveService.create(payload, user_id=user_data.get('id_user')), status=201)


@bp_employee_leave.route('/<id_employee_leave>', methods=['PUT'])
@token_required
@require_entity_permission('employee_leave', 'update')
def update_employee_leave(user_data, id_employee_leave):
    payload = _filter_payload_for_actor(request.get_json() or {}, user_data)
    return _jsonify_projected_record(user_data, EmployeeLeaveService.update(id_employee_leave, payload, user_id=user_data.get('id_user')))


@bp_employee_leave.route('/<id_employee_leave>', methods=['DELETE'])
@token_required
@require_entity_permission('employee_leave', 'delete')
def delete_employee_leave(user_data, id_employee_leave):
    return jsonify(EmployeeLeaveService.delete(id_employee_leave, user_id=user_data.get('id_user')))


@bp_employee_leave.route('/balances', methods=['GET'])
@token_required
@require_entity_permission('employee_leave', 'read')
def employee_leave_balances(user_data):
    """Saldo de vacaciones de cada empleado al dia de hoy (ver employee_leave_service)."""
    from app.services.employee_leave_service import saldos
    return jsonify({'employees': saldos()})



# Solicitudes del propio empleado ("Mis vacaciones"): exigen la capacidad
# `my_leaves`, que el Gestor concede o quita por rol; sobre QUE solicitudes se
# actua (lo propio, su equipo o RH) lo sigue decidiendo employee_leave_service.
@bp_employee_leave.route('/mine', methods=['GET'])
@token_required
@require_entity_permission('my_leaves', 'read')
def my_employee_leaves(user_data):
    """Saldo y ausencias del propio empleado."""
    from app.services.employee_leave_service import mis_ausencias
    return jsonify(mis_ausencias(user_data.get('id_user')))


@bp_employee_leave.route('/request', methods=['POST'])
@token_required
@require_entity_permission('my_leaves', 'create')
def request_employee_leave(user_data):
    """El empleado pide vacaciones o un permiso; queda pendiente de autorizar."""
    from app.services.employee_leave_service import solicitar
    return jsonify(solicitar(user_data.get('id_user'), request.get_json() or {})), 201


@bp_employee_leave.route('/<id_employee_leave>/cancel', methods=['POST'])
@token_required
@require_entity_permission('my_leaves', 'update')
def cancel_employee_leave(user_data, id_employee_leave):
    """El empleado cancela su solicitud pendiente."""
    from app.services.employee_leave_service import cancelar
    return jsonify(cancelar(user_data.get('id_user'), id_employee_leave))


@bp_employee_leave.route('/pending', methods=['GET'])
@token_required
@require_entity_permission('my_leaves', 'read')
def pending_employee_leaves(user_data):
    """Solicitudes por autorizar: las del equipo del supervisor, o todas para RH."""
    from app.services.employee_leave_service import por_autorizar
    return jsonify({'requests': por_autorizar(user_data)})


@bp_employee_leave.route('/<id_employee_leave>/approve', methods=['POST'])
@token_required
@require_entity_permission('my_leaves', 'update')
def approve_employee_leave(user_data, id_employee_leave):
    """Aprueba una solicitud (su supervisor o RH); se vuelven a validar saldo y fechas."""
    from app.services.employee_leave_service import revisar
    return jsonify(revisar(user_data, id_employee_leave, True, (request.get_json(silent=True) or {}).get('review_note')))


@bp_employee_leave.route('/<id_employee_leave>/reject', methods=['POST'])
@token_required
@require_entity_permission('my_leaves', 'update')
def reject_employee_leave(user_data, id_employee_leave):
    """Rechaza una solicitud (su supervisor o RH), con nota opcional."""
    from app.services.employee_leave_service import revisar
    return jsonify(revisar(user_data, id_employee_leave, False, (request.get_json(silent=True) or {}).get('review_note')))


# Hoja de incapacidad: solo exigen sesion; quien la ve o la sube (el propio
# empleado o RH) lo decide employee_leave_document_service.
def _almacen():
    from app.services.document_service import SecureDocumentStorage
    return SecureDocumentStorage(current_app.config["UPLOAD_ROOT"])


@bp_employee_leave.route('/<id_employee_leave>/documents', methods=['GET'])
@token_required
def list_employee_leave_documents(user_data, id_employee_leave):
    """Las hojas de una incapacidad (la ultima primero)."""
    from app.services.employee_leave_document_service import listar
    return jsonify({'documents': listar(id_employee_leave, user_data)})


@bp_employee_leave.route('/<id_employee_leave>/documents', methods=['POST'])
@token_required
def upload_employee_leave_document(user_data, id_employee_leave):
    """Sube una hoja de incapacidad (JPG, PNG o PDF de hasta 10 MB)."""
    from app.services.employee_leave_document_service import subir
    archivo = request.files.get('file')
    if not archivo or not archivo.filename:
        return jsonify({'error_key': 'errors.invalid_field', 'meta': {'field': 'file'}}), 400
    return jsonify(subir(id_employee_leave, user_data, archivo.read(), archivo.filename, _almacen())), 201


@bp_employee_leave.route('/<id_employee_leave>/documents/<int:version>/content', methods=['GET'])
@token_required
def employee_leave_document_content(user_data, id_employee_leave, version):
    """La hoja en el navegador (PDF e imagenes se muestran; ?download=1 la baja)."""
    from app.services.employee_leave_document_service import contenido
    ruta, mime, nombre = contenido(id_employee_leave, version, user_data, _almacen())
    respuesta = send_file(ruta, mimetype=mime, as_attachment=request.args.get('download') == '1', download_name=nombre)
    respuesta.headers['X-Content-Type-Options'] = 'nosniff'
    return respuesta
