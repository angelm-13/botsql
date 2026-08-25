from flask import Blueprint, jsonify, request

from app.services.logistics_unit_service import LogisticsUnitService
from app.utils.auth import require_entity_permission, token_required


bp_logistics_unit = Blueprint('logistics_unit', __name__, url_prefix='/logistics_unit')
ALLOWED_FIELDS = {
    'id_logistics_unit', 'plate', 'unit_type', 'mileage', 'availability_status',
    'insurance_expiration', 'verification_expiration', 'policy_number', 'fuel_efficiency',
    'status', 'created_by', 'creation_date', 'last_update_date', 'deletion_date',
}


@bp_logistics_unit.get('/')
@token_required
@require_entity_permission('logistics_unit', 'read')
def list_logistics_units(user_data):
    filters = {key: value for key, value in request.args.items() if key in ALLOWED_FIELDS}
    return jsonify(LogisticsUnitService.list(page=int(request.args.get('page', 1)), per_page=int(request.args.get('per_page', 20)), filters=filters, sort=request.args.get('sort')))


@bp_logistics_unit.get('/<int:item_id>')
@token_required
@require_entity_permission('logistics_unit', 'read')
def get_logistics_unit(user_data, item_id):
    return jsonify(LogisticsUnitService.get(item_id))


@bp_logistics_unit.post('/')
@token_required
@require_entity_permission('logistics_unit', 'create')
def create_logistics_unit(user_data):
    return jsonify(LogisticsUnitService.create(request.get_json() or {}, user_id=user_data.get('id_user'))), 201


@bp_logistics_unit.put('/<int:item_id>')
@token_required
@require_entity_permission('logistics_unit', 'update')
def update_logistics_unit(user_data, item_id):
    return jsonify(LogisticsUnitService.update(item_id, request.get_json() or {}, user_id=user_data.get('id_user')))


@bp_logistics_unit.delete('/<int:item_id>')
@token_required
@require_entity_permission('logistics_unit', 'delete')
def delete_logistics_unit(user_data, item_id):
    return jsonify(LogisticsUnitService.delete(item_id, user_id=user_data.get('id_user')))