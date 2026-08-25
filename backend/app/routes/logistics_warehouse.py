from flask import Blueprint, jsonify, request

from app.services.logistics_warehouse_service import LogisticsWarehouseService
from app.utils.auth import require_entity_permission, token_required


bp_logistics_warehouse = Blueprint('logistics_warehouse', __name__, url_prefix='/logistics_warehouse')
ALLOWED_FIELDS = {column.name for column in LogisticsWarehouseService.model.__table__.columns}


@bp_logistics_warehouse.get('/')
@token_required
@require_entity_permission('logistics_warehouse', 'read')
def list_logistics_warehouses(user_data):
    filters = {key: value for key, value in request.args.items() if key in ALLOWED_FIELDS}
    return jsonify(LogisticsWarehouseService.list(page=int(request.args.get('page', 1)), per_page=int(request.args.get('per_page', 20)), filters=filters, sort=request.args.get('sort')))


@bp_logistics_warehouse.get('/<int:item_id>')
@token_required
@require_entity_permission('logistics_warehouse', 'read')
def get_logistics_warehouse(user_data, item_id):
    return jsonify(LogisticsWarehouseService.get(item_id))


@bp_logistics_warehouse.post('/')
@token_required
@require_entity_permission('logistics_warehouse', 'create')
def create_logistics_warehouse(user_data):
    return jsonify(LogisticsWarehouseService.create(request.get_json() or {}, user_id=user_data.get('id_user'))), 201


@bp_logistics_warehouse.put('/<int:item_id>')
@token_required
@require_entity_permission('logistics_warehouse', 'update')
def update_logistics_warehouse(user_data, item_id):
    return jsonify(LogisticsWarehouseService.update(item_id, request.get_json() or {}, user_id=user_data.get('id_user')))


@bp_logistics_warehouse.delete('/<int:item_id>')
@token_required
@require_entity_permission('logistics_warehouse', 'delete')
def delete_logistics_warehouse(user_data, item_id):
    return jsonify(LogisticsWarehouseService.delete(item_id, user_id=user_data.get('id_user')))