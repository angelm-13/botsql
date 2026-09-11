from __future__ import annotations
from flask import Blueprint, jsonify, request
from app.services.project_management_service import (
    add_project_message,
    add_project_payment,
    create_project,
    delete_project,
    delete_project_payment,
    get_project_detail,
    list_project_payments,
    list_projects,
    settle_project_payment,
    transition_management,
    transition_project,
    update_project,
)
from app.utils.auth import token_required, require_entity_permission

bp_proyect = Blueprint('proyect', __name__, url_prefix='/proyect')
# Los campos que la respuesta puede llevar. Es una lista blanca: lo que no
# este aqui se recorta antes de salir, aunque el modelo lo tenga. Los de la
# orden de trabajo se agregaron con la migracion 20260911180000 -- sin esto
# estarian en la base y nunca llegarian a la pantalla.
ALLOWED_FIELDS = [
    'id_proyect', 'id_customer_supplier', 'leader', 'proyect_description',
    'title', 'proyect_status', 'created_by', 'creation_date',
    'last_update_date', 'deletion_date',
    'folio', 'requested_by', 'id_quotation', 'purchase_order',
    'purchase_order_item', 'id_supervisor', 'delivery_date',
    'id_drawing_document', 'management_status',
]

TECHNICAL_RESPONSE_FIELDS = {'id_proyect', 'folio', 'submitted_date'}
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
            .filter(Field.table_name == 'proyect')
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



@bp_proyect.route('/', methods=['GET'])
@token_required
@require_entity_permission('proyect', 'read')
def list_proyect(user_data):
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    sort = request.args.get('sort')
    filters = {
        key: value for key, value in request.args.items()
        if key in {'proyect_status', 'created_by', 'id_customer_supplier', 'search', 'creation_date_from', 'creation_date_to'}
    }
    return jsonify(list_projects(user_data, page=page, per_page=per_page, filters=filters, sort=sort))


@bp_proyect.route('/<id_proyect>', methods=['GET'])
@token_required
@require_entity_permission('proyect', 'read')
def get_proyect(user_data, id_proyect):
    return jsonify(get_project_detail(id_proyect, user_data))


@bp_proyect.route('/', methods=['POST'])
@token_required
@require_entity_permission('proyect', 'create')
def create_proyect(user_data):
    return jsonify(create_project(request.get_json() or {}, user_data)), 201


@bp_proyect.route('/<id_proyect>', methods=['PUT'])
@token_required
@require_entity_permission('proyect', 'update')
def update_proyect(user_data, id_proyect):
    return jsonify(update_project(id_proyect, request.get_json() or {}, user_data))


@bp_proyect.route('/<id_proyect>/transition', methods=['POST'])
@token_required
@require_entity_permission('proyect', 'update')
def transition_proyect(user_data, id_proyect):
    return jsonify(transition_project(id_proyect, request.get_json() or {}, user_data))


@bp_proyect.route('/<id_proyect>/management-transition', methods=['POST'])
@token_required
@require_entity_permission('proyect', 'update')
def transition_proyect_management(user_data, id_proyect):
    """El recorrido de GERENCIA, aparte del de taller.

    Dos rutas y no una con un parametro: son dos maquinas de estados con
    transiciones distintas, y mezclarlas en un endpoint obligaria a que el
    cuerpo dijera cual, que es la clase de bifurcacion que acaba validando mal
    la que se usa menos.
    """
    return jsonify(transition_management(id_proyect, request.get_json() or {}, user_data))


# --- parcialidades de pago ---------------------------------------------
# Cuelgan del proyecto y no de un modulo de cobranza propio: lo que se acuerda
# es "40% al pedir ESTE trabajo", y fuera del proyecto la cifra no dice nada.

@bp_proyect.route('/<id_proyect>/payments', methods=['GET'])
@token_required
@require_entity_permission('proyect', 'read')
def list_proyect_payments(user_data, id_proyect):
    return jsonify(list_project_payments(id_proyect, user_data))


@bp_proyect.route('/<id_proyect>/payments', methods=['POST'])
@token_required
@require_entity_permission('proyect', 'update')
def create_proyect_payment(user_data, id_proyect):
    return jsonify(add_project_payment(id_proyect, request.get_json() or {}, user_data)), 201


@bp_proyect.route('/payments/<id_payment>', methods=['PUT'])
@token_required
@require_entity_permission('proyect', 'update')
def settle_proyect_payment(user_data, id_payment):
    return jsonify(settle_project_payment(id_payment, request.get_json() or {}, user_data))


@bp_proyect.route('/payments/<id_payment>', methods=['DELETE'])
@token_required
@require_entity_permission('proyect', 'delete')
def remove_proyect_payment(user_data, id_payment):
    return jsonify(delete_project_payment(id_payment, user_data))


@bp_proyect.route('/<id_proyect>/messages', methods=['POST'])
@token_required
@require_entity_permission('proyect', 'update')
def create_proyect_message(user_data, id_proyect):
    return jsonify(add_project_message(id_proyect, request.get_json() or {}, user_data)), 201


@bp_proyect.route('/<id_proyect>', methods=['DELETE'])
@token_required
@require_entity_permission('proyect', 'delete')
def delete_proyect(user_data, id_proyect):
    return jsonify(delete_project(id_proyect, user_data))
