from flask import Blueprint, jsonify, request

from app.services.logistics_contact_service import LogisticsContactService
from app.utils.auth import require_entity_permission, token_required


bp_logistics_contact = Blueprint('logistics_contact', __name__, url_prefix='/logistics_contact')
ALLOWED_FIELDS = {
    'id_logistics_contact', 'id_customer_supplier', 'full_name', 'email', 'phone',
    'position', 'status', 'created_by', 'creation_date', 'last_update_date', 'deletion_date',
}


@bp_logistics_contact.get('/')
@token_required
@require_entity_permission('logistics_contact', 'read')
def list_logistics_contacts(user_data):
    filters = {key: value for key, value in request.args.items() if key in ALLOWED_FIELDS}
    return jsonify(LogisticsContactService.list(
        page=int(request.args.get('page', 1)),
        per_page=int(request.args.get('per_page', 20)),
        filters=filters,
        sort=request.args.get('sort'),
    ))


@bp_logistics_contact.get('/<int:contact_id>')
@token_required
@require_entity_permission('logistics_contact', 'read')
def get_logistics_contact(user_data, contact_id):
    return jsonify(LogisticsContactService.get(contact_id))


@bp_logistics_contact.post('/')
@token_required
@require_entity_permission('logistics_contact', 'create')
def create_logistics_contact(user_data):
    return jsonify(LogisticsContactService.create(request.get_json() or {}, user_id=user_data.get('id_user'))), 201


@bp_logistics_contact.put('/<int:contact_id>')
@token_required
@require_entity_permission('logistics_contact', 'update')
def update_logistics_contact(user_data, contact_id):
    return jsonify(LogisticsContactService.update(contact_id, request.get_json() or {}, user_id=user_data.get('id_user')))


@bp_logistics_contact.delete('/<int:contact_id>')
@token_required
@require_entity_permission('logistics_contact', 'delete')
def delete_logistics_contact(user_data, contact_id):
    return jsonify(LogisticsContactService.delete(contact_id, user_id=user_data.get('id_user')))