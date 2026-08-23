from flask import Blueprint, jsonify, request

from app.services.logistics_rate_service import LogisticsRateService
from app.utils.auth import require_entity_permission, token_required


bp_logistics_rate = Blueprint('logistics_rate', __name__, url_prefix='/logistics_rate')
ALLOWED_FIELDS = {
    'id_logistics_rate', 'id_customer_supplier', 'service_type', 'origin', 'destination',
    'unit_type', 'amount', 'currency', 'status', 'created_by', 'creation_date',
    'last_update_date', 'deletion_date',
}


@bp_logistics_rate.get('/')
@token_required
@require_entity_permission('logistics_rate', 'read')
def list_logistics_rates(user_data):
    filters = {key: value for key, value in request.args.items() if key in ALLOWED_FIELDS}
    return jsonify(LogisticsRateService.list(page=int(request.args.get('page', 1)), per_page=int(request.args.get('per_page', 20)), filters=filters, sort=request.args.get('sort')))


@bp_logistics_rate.get('/<int:item_id>')
@token_required
@require_entity_permission('logistics_rate', 'read')
def get_logistics_rate(user_data, item_id):
    return jsonify(LogisticsRateService.get(item_id))


@bp_logistics_rate.post('/')
@token_required
@require_entity_permission('logistics_rate', 'create')
def create_logistics_rate(user_data):
    return jsonify(LogisticsRateService.create(request.get_json() or {}, user_id=user_data.get('id_user'))), 201


@bp_logistics_rate.put('/<int:item_id>')
@token_required
@require_entity_permission('logistics_rate', 'update')
def update_logistics_rate(user_data, item_id):
    return jsonify(LogisticsRateService.update(item_id, request.get_json() or {}, user_id=user_data.get('id_user')))


@bp_logistics_rate.delete('/<int:item_id>')
@token_required
@require_entity_permission('logistics_rate', 'delete')
def delete_logistics_rate(user_data, item_id):
    return jsonify(LogisticsRateService.delete(item_id, user_id=user_data.get('id_user')))