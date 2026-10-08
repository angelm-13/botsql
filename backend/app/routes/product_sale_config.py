from __future__ import annotations
from flask import Blueprint, jsonify, request
from app.services.product_sale_config_service import ProductSaleConfigService
from app.utils.auth import token_required, require_entity_permission
from app.utils.errors import AppError
from app.utils.field_access import COLUMNAS_DE_AUDITORIA

bp_product_sale_config = Blueprint('product_sale_config', __name__, url_prefix='/product_sale_config')
ALLOWED_FIELDS = ['id_product_sale_config', 'id_product', 'margin_percent', 'manual_price', 'id_inventory_status', 'is_active', 'created_by', 'creation_date', 'last_update_date', 'deletion_date']

TECHNICAL_RESPONSE_FIELDS = {'id_product_sale_config'}
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
            .filter(Field.table_name == 'product_sale_config')
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



@bp_product_sale_config.route('/', methods=['GET'])
@token_required
@require_entity_permission('product_sale_config', 'read')
def list_product_sale_config(user_data):
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    sort = request.args.get('sort')
    filters = {k: v for k, v in request.args.items() if k not in {'page', 'per_page', 'sort', 'q'} and k in ALLOWED_FIELDS}
    return _jsonify_projected_list(user_data, ProductSaleConfigService.list(page=page, per_page=per_page, filters=filters, sort=sort, q=request.args.get('q')))


@bp_product_sale_config.route('/<id_product_sale_config>', methods=['GET'])
@token_required
@require_entity_permission('product_sale_config', 'read')
def get_product_sale_config(user_data, id_product_sale_config):
    return _jsonify_projected_record(user_data, ProductSaleConfigService.get(id_product_sale_config))


@bp_product_sale_config.route('/', methods=['POST'])
@token_required
@require_entity_permission('product_sale_config', 'create')
def create_product_sale_config(user_data):
    payload = _filter_payload_for_actor(request.get_json() or {}, user_data)
    return _jsonify_projected_record(user_data, ProductSaleConfigService.create(payload, user_id=user_data.get('id_user')), status=201)


@bp_product_sale_config.route('/<id_product_sale_config>', methods=['PUT'])
@token_required
@require_entity_permission('product_sale_config', 'update')
def update_product_sale_config(user_data, id_product_sale_config):
    payload = _filter_payload_for_actor(request.get_json() or {}, user_data)
    return _jsonify_projected_record(user_data, ProductSaleConfigService.update(id_product_sale_config, payload, user_id=user_data.get('id_user')))


@bp_product_sale_config.route('/<id_product_sale_config>', methods=['DELETE'])
@token_required
@require_entity_permission('product_sale_config', 'delete')
def delete_product_sale_config(user_data, id_product_sale_config):
    return jsonify(ProductSaleConfigService.delete(id_product_sale_config, user_id=user_data.get('id_user')))
