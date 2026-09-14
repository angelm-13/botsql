from flask import Blueprint, jsonify, request

from app.services.logistics_rack_service import LogisticsRackService
from app.utils.auth import require_entity_permission, token_required


bp_logistics_rack = Blueprint('logistics_rack', __name__, url_prefix='/logistics_rack')
ALLOWED_FIELDS = {column.name for column in LogisticsRackService.model.__table__.columns}


@bp_logistics_rack.get('/')
@token_required
@require_entity_permission('logistics_rack', 'read')
def list_logistics_racks(user_data):
    filters = {key: value for key, value in request.args.items() if key in ALLOWED_FIELDS}
    return jsonify(LogisticsRackService.list(page=int(request.args.get('page', 1)), per_page=int(request.args.get('per_page', 20)), filters=filters, sort=request.args.get('sort')))


@bp_logistics_rack.get('/<int:item_id>')
@token_required
@require_entity_permission('logistics_rack', 'read')
def get_logistics_rack(user_data, item_id):
    return jsonify(LogisticsRackService.get(item_id))


@bp_logistics_rack.post('/')
@token_required
@require_entity_permission('logistics_rack', 'create')
def create_logistics_rack(user_data):
    return jsonify(LogisticsRackService.create(request.get_json() or {}, user_id=user_data.get('id_user'))), 201


@bp_logistics_rack.put('/<int:item_id>')
@token_required
@require_entity_permission('logistics_rack', 'update')
def update_logistics_rack(user_data, item_id):
    return jsonify(LogisticsRackService.update(item_id, request.get_json() or {}, user_id=user_data.get('id_user')))


@bp_logistics_rack.delete('/<int:item_id>')
@token_required
@require_entity_permission('logistics_rack', 'delete')
def delete_logistics_rack(user_data, item_id):
    return jsonify(LogisticsRackService.delete(item_id, user_id=user_data.get('id_user')))