from flask import Blueprint, jsonify, request

from app.services.logistics_trailer_service import LogisticsTrailerService
from app.utils.auth import require_entity_permission, token_required


bp_logistics_trailer = Blueprint('logistics_trailer', __name__, url_prefix='/logistics_trailer')
ALLOWED_FIELDS = {
    'id_logistics_trailer', 'plate', 'trailer_type', 'capacity', 'status',
    'created_by', 'creation_date', 'last_update_date', 'deletion_date',
}


@bp_logistics_trailer.get('/')
@token_required
@require_entity_permission('logistics_trailer', 'read')
def list_logistics_trailers(user_data):
    filters = {key: value for key, value in request.args.items() if key in ALLOWED_FIELDS}
    return jsonify(LogisticsTrailerService.list(page=int(request.args.get('page', 1)), per_page=int(request.args.get('per_page', 20)), filters=filters, sort=request.args.get('sort')))


@bp_logistics_trailer.get('/<int:item_id>')
@token_required
@require_entity_permission('logistics_trailer', 'read')
def get_logistics_trailer(user_data, item_id):
    return jsonify(LogisticsTrailerService.get(item_id))


@bp_logistics_trailer.post('/')
@token_required
@require_entity_permission('logistics_trailer', 'create')
def create_logistics_trailer(user_data):
    return jsonify(LogisticsTrailerService.create(request.get_json() or {}, user_id=user_data.get('id_user'))), 201


@bp_logistics_trailer.put('/<int:item_id>')
@token_required
@require_entity_permission('logistics_trailer', 'update')
def update_logistics_trailer(user_data, item_id):
    return jsonify(LogisticsTrailerService.update(item_id, request.get_json() or {}, user_id=user_data.get('id_user')))


@bp_logistics_trailer.delete('/<int:item_id>')
@token_required
@require_entity_permission('logistics_trailer', 'delete')
def delete_logistics_trailer(user_data, item_id):
    return jsonify(LogisticsTrailerService.delete(item_id, user_id=user_data.get('id_user')))