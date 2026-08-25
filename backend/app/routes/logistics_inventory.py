from flask import Blueprint, jsonify, request

from app.services.logistics_inventory_service import LogisticsInventoryService
from app.utils.auth import require_entity_permission, token_required


bp_logistics_inventory = Blueprint('logistics_inventory', __name__, url_prefix='/logistics_inventory')
ALLOWED_FIELDS = {column.name for column in LogisticsInventoryService.model.__table__.columns}


@bp_logistics_inventory.get('/')
@token_required
@require_entity_permission('logistics_inventory', 'read')
def list_logistics_inventory(user_data):
    filters = {key: value for key, value in request.args.items() if key in ALLOWED_FIELDS}
    return jsonify(LogisticsInventoryService.list(page=int(request.args.get('page', 1)), per_page=int(request.args.get('per_page', 20)), filters=filters, sort=request.args.get('sort')))


@bp_logistics_inventory.get('/<int:item_id>')
@token_required
@require_entity_permission('logistics_inventory', 'read')
def get_logistics_inventory(user_data, item_id):
    return jsonify(LogisticsInventoryService.get(item_id))


@bp_logistics_inventory.post('/')
@token_required
@require_entity_permission('logistics_inventory', 'create')
def create_logistics_inventory(user_data):
    return jsonify(LogisticsInventoryService.create(request.get_json() or {}, user_id=user_data.get('id_user'))), 201


@bp_logistics_inventory.put('/<int:item_id>')
@token_required
@require_entity_permission('logistics_inventory', 'update')
def update_logistics_inventory(user_data, item_id):
    return jsonify(LogisticsInventoryService.update(item_id, request.get_json() or {}, user_id=user_data.get('id_user')))


@bp_logistics_inventory.delete('/<int:item_id>')
@token_required
@require_entity_permission('logistics_inventory', 'delete')
def delete_logistics_inventory(user_data, item_id):
    return jsonify(LogisticsInventoryService.delete(item_id, user_id=user_data.get('id_user')))