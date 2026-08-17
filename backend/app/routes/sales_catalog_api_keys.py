from __future__ import annotations
from datetime import datetime, timezone
from flask import Blueprint, jsonify, request
from app.models import PublicApiKey
from app.models.session import transaction_context
from app.services.public_api_key_manager import PublicApiKeyManager
from app.utils.auth import token_required, require_entity_permission
from app.utils.errors import AppError


bp_sales_catalog_api_keys = Blueprint('sales_catalog_api_keys', __name__, url_prefix='/sales-catalog/api-keys')


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _to_int(value, default=60):
    if value in (None, ''):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _get_key_or_404(session, id_public_api_key):
    record = (
        session.query(PublicApiKey)
        .filter(PublicApiKey.id_public_api_key == id_public_api_key)
        .filter(PublicApiKey.deletion_date.is_(None))
        .first()
    )
    if not record:
        raise AppError('errors.not_found', 404, {'entity': 'public_api_key', 'id': id_public_api_key})
    return record


@bp_sales_catalog_api_keys.route('', methods=['GET'])
@token_required
@require_entity_permission('public_api_key', 'read')
def list_catalog_api_keys(user_data):
    with transaction_context() as session:
        rows = (
            session.query(PublicApiKey)
            .filter(PublicApiKey.deletion_date.is_(None))
            .order_by(PublicApiKey.id_public_api_key.asc())
            .all()
        )
        items = [PublicApiKeyManager.safe_serialize(row) for row in rows]
    return jsonify({'items': items, 'total': len(items)})


@bp_sales_catalog_api_keys.route('', methods=['POST'])
@token_required
@require_entity_permission('public_api_key', 'create')
def create_catalog_api_key(user_data):
    payload = request.get_json() or {}
    result = PublicApiKeyManager.create_key(
        label=payload.get('label'),
        allowed_domains=payload.get('allowed_domains') or '[]',
        rate_limit_per_min=payload.get('rate_limit_per_min') or PublicApiKeyManager.default_rate_limit(),
        user_id=user_data.get('id_user'),
    )
    return jsonify(result), 201


@bp_sales_catalog_api_keys.route('/<int:id_public_api_key>', methods=['PATCH'])
@token_required
@require_entity_permission('public_api_key', 'update')
def update_catalog_api_key(user_data, id_public_api_key):
    payload = request.get_json() or {}
    with transaction_context() as session:
        record = _get_key_or_404(session, id_public_api_key)
        if 'label' in payload:
            record.label = str(payload.get('label') or '').strip() or record.label
        if 'allowed_domains' in payload:
            record.allowed_domains = payload.get('allowed_domains') or '[]'
        if 'rate_limit_per_min' in payload:
            rate_limit = _to_int(payload.get('rate_limit_per_min'), record.rate_limit_per_min or PublicApiKeyManager.default_rate_limit())
            if rate_limit < 1:
                raise AppError('errors.invalid_field', 400, {'field': 'rate_limit_per_min'})
            record.rate_limit_per_min = rate_limit
        if 'is_active' in payload:
            record.is_active = bool(payload.get('is_active'))
        record.last_update_date = _now()
        session.flush()
        result = PublicApiKeyManager.safe_serialize(record)
    return jsonify(result)


@bp_sales_catalog_api_keys.route('/<int:id_public_api_key>/revoke', methods=['POST'])
@token_required
@require_entity_permission('public_api_key', 'delete')
def revoke_catalog_api_key(user_data, id_public_api_key):
    with transaction_context() as session:
        record = _get_key_or_404(session, id_public_api_key)
        record.is_active = False
        record.last_update_date = _now()
        session.flush()
        result = PublicApiKeyManager.safe_serialize(record)
    return jsonify(result)
