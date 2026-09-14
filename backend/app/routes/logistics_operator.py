from flask import Blueprint, jsonify, request

from app.services.logistics_operator_service import LogisticsOperatorService
from app.utils.auth import require_entity_permission, token_required


bp_logistics_operator = Blueprint('logistics_operator', __name__, url_prefix='/logistics_operator')
ALLOWED_FIELDS = {
    'id_logistics_operator', 'full_name', 'license_number', 'license_expiration',
    'status', 'contact_phone', 'performance_score', 'created_by', 'creation_date',
    'last_update_date', 'deletion_date',
}


@bp_logistics_operator.get('/')
@token_required
@require_entity_permission('logistics_operator', 'read')
def list_logistics_operators(user_data):
    filters = {key: value for key, value in request.args.items() if key in ALLOWED_FIELDS}
    return jsonify(LogisticsOperatorService.list(page=int(request.args.get('page', 1)), per_page=int(request.args.get('per_page', 20)), filters=filters, sort=request.args.get('sort')))


@bp_logistics_operator.get('/<int:item_id>')
@token_required
@require_entity_permission('logistics_operator', 'read')
def get_logistics_operator(user_data, item_id):
    return jsonify(LogisticsOperatorService.get(item_id))


@bp_logistics_operator.post('/')
@token_required
@require_entity_permission('logistics_operator', 'create')
def create_logistics_operator(user_data):
    return jsonify(LogisticsOperatorService.create(request.get_json() or {}, user_id=user_data.get('id_user'))), 201


@bp_logistics_operator.put('/<int:item_id>')
@token_required
@require_entity_permission('logistics_operator', 'update')
def update_logistics_operator(user_data, item_id):
    return jsonify(LogisticsOperatorService.update(item_id, request.get_json() or {}, user_id=user_data.get('id_user')))


@bp_logistics_operator.delete('/<int:item_id>')
@token_required
@require_entity_permission('logistics_operator', 'delete')
def delete_logistics_operator(user_data, item_id):
    return jsonify(LogisticsOperatorService.delete(item_id, user_id=user_data.get('id_user')))