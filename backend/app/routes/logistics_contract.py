from flask import Blueprint, jsonify, request

from app.services.logistics_contract_service import LogisticsContractService
from app.utils.auth import require_entity_permission, token_required


bp_logistics_contract = Blueprint('logistics_contract', __name__, url_prefix='/logistics_contract')
ALLOWED_FIELDS = {
    'id_logistics_contract', 'id_customer_supplier', 'contract_number', 'start_date', 'end_date',
    'sla_level', 'status', 'created_by', 'creation_date', 'last_update_date', 'deletion_date',
}


@bp_logistics_contract.get('/')
@token_required
@require_entity_permission('logistics_contract', 'read')
def list_logistics_contracts(user_data):
    filters = {key: value for key, value in request.args.items() if key in ALLOWED_FIELDS}
    return jsonify(LogisticsContractService.list(page=int(request.args.get('page', 1)), per_page=int(request.args.get('per_page', 20)), filters=filters, sort=request.args.get('sort')))


@bp_logistics_contract.get('/<int:item_id>')
@token_required
@require_entity_permission('logistics_contract', 'read')
def get_logistics_contract(user_data, item_id):
    return jsonify(LogisticsContractService.get(item_id))


@bp_logistics_contract.post('/')
@token_required
@require_entity_permission('logistics_contract', 'create')
def create_logistics_contract(user_data):
    return jsonify(LogisticsContractService.create(request.get_json() or {}, user_id=user_data.get('id_user'))), 201


@bp_logistics_contract.put('/<int:item_id>')
@token_required
@require_entity_permission('logistics_contract', 'update')
def update_logistics_contract(user_data, item_id):
    return jsonify(LogisticsContractService.update(item_id, request.get_json() or {}, user_id=user_data.get('id_user')))


@bp_logistics_contract.delete('/<int:item_id>')
@token_required
@require_entity_permission('logistics_contract', 'delete')
def delete_logistics_contract(user_data, item_id):
    return jsonify(LogisticsContractService.delete(item_id, user_id=user_data.get('id_user')))