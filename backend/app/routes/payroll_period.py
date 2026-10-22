from __future__ import annotations
from flask import Blueprint, jsonify, request
from app.services.payroll_period_service import PayrollPeriodService
from app.utils.auth import token_required, require_entity_permission
from app.utils.errors import AppError
from app.utils.field_access import COLUMNAS_DE_AUDITORIA

bp_payroll_period = Blueprint('payroll_period', __name__, url_prefix='/payroll_period')
ALLOWED_FIELDS = ['id_payroll_period', 'period_start', 'period_end', 'payment_date', 'id_status', 'created_by', 'creation_date', 'last_update_date', 'deletion_date', 'period_state', 'closed_at', 'closed_by', 'reopened_at', 'reopened_by', 'includes_aguinaldo']

TECHNICAL_RESPONSE_FIELDS = {'id_payroll_period'}
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
            .filter(Field.table_name == 'payroll_period')
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



@bp_payroll_period.route('/', methods=['GET'])
@token_required
@require_entity_permission('payroll_period', 'read')
def list_payroll_period(user_data):
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    sort = request.args.get('sort')
    filters = {k: v for k, v in request.args.items() if k not in {'page', 'per_page', 'sort', 'q'} and k in ALLOWED_FIELDS}
    return _jsonify_projected_list(user_data, PayrollPeriodService.list(page=page, per_page=per_page, filters=filters, sort=sort, q=request.args.get('q')))


@bp_payroll_period.route('/<id_payroll_period>', methods=['GET'])
@token_required
@require_entity_permission('payroll_period', 'read')
def get_payroll_period(user_data, id_payroll_period):
    return _jsonify_projected_record(user_data, PayrollPeriodService.get(id_payroll_period))


@bp_payroll_period.route('/', methods=['POST'])
@token_required
@require_entity_permission('payroll_period', 'create')
def create_payroll_period(user_data):
    payload = _filter_payload_for_actor(request.get_json() or {}, user_data)
    return _jsonify_projected_record(user_data, PayrollPeriodService.create(payload, user_id=user_data.get('id_user')), status=201)


@bp_payroll_period.route('/<id_payroll_period>', methods=['PUT'])
@token_required
@require_entity_permission('payroll_period', 'update')
def update_payroll_period(user_data, id_payroll_period):
    payload = _filter_payload_for_actor(request.get_json() or {}, user_data)
    return _jsonify_projected_record(user_data, PayrollPeriodService.update(id_payroll_period, payload, user_id=user_data.get('id_user')))


@bp_payroll_period.route('/<id_payroll_period>', methods=['DELETE'])
@token_required
@require_entity_permission('payroll_period', 'delete')
def delete_payroll_period(user_data, id_payroll_period):
    return jsonify(PayrollPeriodService.delete(id_payroll_period, user_id=user_data.get('id_user')))


@bp_payroll_period.route('/<id_payroll_period>/calculate', methods=['POST'])
@token_required
@require_entity_permission('payroll_detail', 'create')
def calculate_payroll_period(user_data, id_payroll_period):
    """Calcula la nomina del periodo con las checadas guardadas (ver payroll_calculation_service)."""
    from app.services.payroll_calculation_service import calcular_periodo
    return jsonify(calcular_periodo(id_payroll_period, user_data.get('id_user')))


@bp_payroll_period.route('/<id_payroll_period>/close', methods=['POST'])
@token_required
@require_entity_permission('payroll_period', 'update')
def close_payroll_period(user_data, id_payroll_period):
    """Congela un periodo ya calculado (ver payroll_calculation_service)."""
    from app.services.payroll_calculation_service import cerrar_periodo
    return jsonify(cerrar_periodo(id_payroll_period, user_data.get('id_user')))


@bp_payroll_period.route('/<id_payroll_period>/reopen', methods=['POST'])
@token_required
# Reabrir es de quien administra nomina: el permiso de borrar periodos, que el
# registro de modulos solo le da a Administrator.
@require_entity_permission('payroll_period', 'delete')
def reopen_payroll_period(user_data, id_payroll_period):
    from app.services.payroll_calculation_service import reabrir_periodo
    return jsonify(reabrir_periodo(id_payroll_period, user_data.get('id_user')))


@bp_payroll_period.route('/<id_payroll_period>/summary', methods=['GET'])
@token_required
@require_entity_permission('payroll_detail', 'read')
def summary_payroll_period(user_data, id_payroll_period):
    """Lo ya calculado del periodo, sin recalcular."""
    from app.services.payroll_calculation_service import resumen_periodo
    return jsonify(resumen_periodo(id_payroll_period))


@bp_payroll_period.route('/<id_payroll_period>/receipt/<id_user>', methods=['GET'])
@token_required
@require_entity_permission('payroll_detail', 'read')
def receipt_payroll_period(user_data, id_payroll_period, id_user):
    """Recibo de nomina en PDF de un empleado (comprobante interno, no CFDI)."""
    from flask import Response
    from app.services.payroll_calculation_service import pdf_del_recibo
    pdf, nombre = pdf_del_recibo(id_payroll_period, id_user)
    return Response(pdf, mimetype='application/pdf',
                    headers={'Content-Disposition': f'inline; filename="{nombre}"'})
