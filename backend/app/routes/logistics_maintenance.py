from flask import Blueprint, jsonify, request

from app.services.logistics_maintenance_service import LogisticsMaintenanceService
from app.utils.auth import require_entity_permission, token_required


bp_logistics_maintenance = Blueprint('logistics_maintenance', __name__, url_prefix='/logistics_maintenance')
ALLOWED_FIELDS = {
    'id_logistics_maintenance', 'id_logistics_unit', 'maintenance_type', 'scheduled_at',
    'closed_at', 'cost', 'status', 'description', 'created_by', 'creation_date',
    'last_update_date', 'deletion_date',
}


@bp_logistics_maintenance.get('/')
@token_required
@require_entity_permission('logistics_maintenance', 'read')
def list_logistics_maintenance(user_data):
    filters = {key: value for key, value in request.args.items() if key in ALLOWED_FIELDS}
    return jsonify(LogisticsMaintenanceService.list(page=int(request.args.get('page', 1)), per_page=int(request.args.get('per_page', 20)), filters=filters, sort=request.args.get('sort')))


@bp_logistics_maintenance.get('/<int:item_id>')
@token_required
@require_entity_permission('logistics_maintenance', 'read')
def get_logistics_maintenance(user_data, item_id):
    return jsonify(LogisticsMaintenanceService.get(item_id))


@bp_logistics_maintenance.post('/')
@token_required
@require_entity_permission('logistics_maintenance', 'create')
def create_logistics_maintenance(user_data):
    return jsonify(LogisticsMaintenanceService.create(request.get_json() or {}, user_id=user_data.get('id_user'))), 201


@bp_logistics_maintenance.put('/<int:item_id>')
@token_required
@require_entity_permission('logistics_maintenance', 'update')
def update_logistics_maintenance(user_data, item_id):
    return jsonify(LogisticsMaintenanceService.update(item_id, request.get_json() or {}, user_id=user_data.get('id_user')))


@bp_logistics_maintenance.delete('/<int:item_id>')
@token_required
@require_entity_permission('logistics_maintenance', 'delete')
def delete_logistics_maintenance(user_data, item_id):
    return jsonify(LogisticsMaintenanceService.delete(item_id, user_id=user_data.get('id_user')))