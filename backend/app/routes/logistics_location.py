from flask import Blueprint, jsonify, request

from app.services.logistics_location_service import LogisticsLocationService
from app.utils.auth import require_entity_permission, token_required


bp_logistics_location = Blueprint('logistics_location', __name__, url_prefix='/logistics_location')
ALLOWED_FIELDS = {column.name for column in LogisticsLocationService.model.__table__.columns}


@bp_logistics_location.get('/')
@token_required
@require_entity_permission('logistics_location', 'read')
def list_logistics_locations(user_data):
    filters = {key: value for key, value in request.args.items() if key in ALLOWED_FIELDS}
    return jsonify(LogisticsLocationService.list(page=int(request.args.get('page', 1)), per_page=int(request.args.get('per_page', 20)), filters=filters, sort=request.args.get('sort')))


@bp_logistics_location.get('/<int:item_id>')
@token_required
@require_entity_permission('logistics_location', 'read')
def get_logistics_location(user_data, item_id):
    return jsonify(LogisticsLocationService.get(item_id))


@bp_logistics_location.post('/')
@token_required
@require_entity_permission('logistics_location', 'create')
def create_logistics_location(user_data):
    return jsonify(LogisticsLocationService.create(request.get_json() or {}, user_id=user_data.get('id_user'))), 201


@bp_logistics_location.put('/<int:item_id>')
@token_required
@require_entity_permission('logistics_location', 'update')
def update_logistics_location(user_data, item_id):
    return jsonify(LogisticsLocationService.update(item_id, request.get_json() or {}, user_id=user_data.get('id_user')))


@bp_logistics_location.delete('/<int:item_id>')
@token_required
@require_entity_permission('logistics_location', 'delete')
def delete_logistics_location(user_data, item_id):
    return jsonify(LogisticsLocationService.delete(item_id, user_id=user_data.get('id_user')))