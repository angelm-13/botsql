from flask import Blueprint, jsonify, request

from app.services.logistics_address_service import LogisticsAddressService
from app.utils.auth import require_entity_permission, token_required


bp_logistics_address = Blueprint('logistics_address', __name__, url_prefix='/logistics_address')
ALLOWED_FIELDS = {
    'id_logistics_address', 'id_customer_supplier', 'name', 'address_line', 'city', 'state',
    'country', 'postal_code', 'address_type', 'status', 'created_by', 'creation_date',
    'last_update_date', 'deletion_date',
}


@bp_logistics_address.get('/')
@token_required
@require_entity_permission('logistics_address', 'read')
def list_logistics_addresses(user_data):
    filters = {key: value for key, value in request.args.items() if key in ALLOWED_FIELDS}
    return jsonify(LogisticsAddressService.list(page=int(request.args.get('page', 1)), per_page=int(request.args.get('per_page', 20)), filters=filters, sort=request.args.get('sort')))


@bp_logistics_address.get('/<int:item_id>')
@token_required
@require_entity_permission('logistics_address', 'read')
def get_logistics_address(user_data, item_id):
    return jsonify(LogisticsAddressService.get(item_id))


@bp_logistics_address.post('/')
@token_required
@require_entity_permission('logistics_address', 'create')
def create_logistics_address(user_data):
    return jsonify(LogisticsAddressService.create(request.get_json() or {}, user_id=user_data.get('id_user'))), 201


@bp_logistics_address.put('/<int:item_id>')
@token_required
@require_entity_permission('logistics_address', 'update')
def update_logistics_address(user_data, item_id):
    return jsonify(LogisticsAddressService.update(item_id, request.get_json() or {}, user_id=user_data.get('id_user')))


@bp_logistics_address.delete('/<int:item_id>')
@token_required
@require_entity_permission('logistics_address', 'delete')
def delete_logistics_address(user_data, item_id):
    return jsonify(LogisticsAddressService.delete(item_id, user_id=user_data.get('id_user')))