from flask import Blueprint, jsonify, request

from app.services.logistics_workflow_service import (
    LogisticsBranchService,
    LogisticsEvidenceService,
    LogisticsFileService,
    LogisticsIncidentService,
    LogisticsQuotationService,
    LogisticsReceivableService,
    LogisticsServiceRequestService,
    LogisticsShipmentService,
    LogisticsTripService,
)
from app.utils.auth import require_entity_permission, token_required


def create_crud_blueprint(entity_name: str, service) -> Blueprint:
    blueprint = Blueprint(entity_name, __name__, url_prefix=f'/{entity_name}')
    allowed_fields = {column.name for column in service.model.__table__.columns}

    @blueprint.get('/')
    @token_required
    @require_entity_permission(entity_name, 'read')
    def list_items(user_data):
        filters = {key: value for key, value in request.args.items() if key in allowed_fields}
        return jsonify(service.list(
            page=int(request.args.get('page', 1)),
            per_page=int(request.args.get('per_page', 20)),
            filters=filters,
            sort=request.args.get('sort'),
        ))

    @blueprint.get('/<int:item_id>')
    @token_required
    @require_entity_permission(entity_name, 'read')
    def get_item(user_data, item_id):
        return jsonify(service.get(item_id))

    @blueprint.post('/')
    @token_required
    @require_entity_permission(entity_name, 'create')
    def create_item(user_data):
        return jsonify(service.create(request.get_json() or {}, user_id=user_data.get('id_user'))), 201

    @blueprint.put('/<int:item_id>')
    @token_required
    @require_entity_permission(entity_name, 'update')
    def update_item(user_data, item_id):
        return jsonify(service.update(item_id, request.get_json() or {}, user_id=user_data.get('id_user')))

    @blueprint.delete('/<int:item_id>')
    @token_required
    @require_entity_permission(entity_name, 'delete')
    def delete_item(user_data, item_id):
        return jsonify(service.delete(item_id, user_id=user_data.get('id_user')))

    return blueprint


bp_logistics_quotation = create_crud_blueprint('logistics_quotation', LogisticsQuotationService)
bp_logistics_service_request = create_crud_blueprint('logistics_service_request', LogisticsServiceRequestService)
bp_logistics_trip = create_crud_blueprint('logistics_trip', LogisticsTripService)
bp_logistics_evidence = create_crud_blueprint('logistics_evidence', LogisticsEvidenceService)
bp_logistics_incident = create_crud_blueprint('logistics_incident', LogisticsIncidentService)
bp_logistics_shipment = create_crud_blueprint('logistics_shipment', LogisticsShipmentService)
bp_logistics_branch = create_crud_blueprint('logistics_branch', LogisticsBranchService)
bp_logistics_receivable = create_crud_blueprint('logistics_receivable', LogisticsReceivableService)
bp_logistics_file = create_crud_blueprint('logistics_file', LogisticsFileService)