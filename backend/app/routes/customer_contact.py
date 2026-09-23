from flask import Blueprint, jsonify, request

from app.services.customer_contact_service import CustomerContactService
from app.utils.auth import require_entity_permission, token_required


bp_customer_contact = Blueprint('customer_contact', __name__, url_prefix='/customer_contact')
ALLOWED_FIELDS = {
    'id_customer_contact', 'id_customer_supplier', 'full_name', 'email', 'phone',
    'position', 'status', 'created_by', 'creation_date', 'last_update_date', 'deletion_date',
}


@bp_customer_contact.get('/options')
@token_required
@require_entity_permission('proyect', 'read')
def list_customer_contact_options(user_data):
    """Quien puede ver proyectos puede elegir un contacto, sin el permiso
    completo de customer_contact -- ver el docstring de
    CustomerContactService.options().
    """
    return jsonify(CustomerContactService.options())


@bp_customer_contact.get('/')
@token_required
@require_entity_permission('customer_contact', 'read')
def list_customer_contacts(user_data):
    filters = {key: value for key, value in request.args.items() if key in ALLOWED_FIELDS}
    return jsonify(CustomerContactService.list(
        page=int(request.args.get('page', 1)),
        per_page=int(request.args.get('per_page', 20)),
        filters=filters,
        sort=request.args.get('sort'),
    ))


@bp_customer_contact.get('/<int:contact_id>')
@token_required
@require_entity_permission('customer_contact', 'read')
def get_customer_contact(user_data, contact_id):
    return jsonify(CustomerContactService.get(contact_id))


@bp_customer_contact.post('/')
@token_required
@require_entity_permission('customer_contact', 'create')
def create_customer_contact(user_data):
    return jsonify(CustomerContactService.create(request.get_json() or {}, user_id=user_data.get('id_user'))), 201


@bp_customer_contact.put('/<int:contact_id>')
@token_required
@require_entity_permission('customer_contact', 'update')
def update_customer_contact(user_data, contact_id):
    return jsonify(CustomerContactService.update(contact_id, request.get_json() or {}, user_id=user_data.get('id_user')))


@bp_customer_contact.delete('/<int:contact_id>')
@token_required
@require_entity_permission('customer_contact', 'delete')
def delete_customer_contact(user_data, contact_id):
    return jsonify(CustomerContactService.delete(contact_id, user_id=user_data.get('id_user')))
