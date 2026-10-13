from __future__ import annotations
import os
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from flask import Blueprint, jsonify, request
from sqlalchemy import and_, or_
from app.models import Product, ProductSaleConfig, InventoryStatus
from app.models.session import transaction_context
from app.services.pricing_service import PricingService
from app.utils.auth import token_required, require_entity_permission
from app.utils.errors import AppError
from app.utils.public_url import image_url


bp_sales_catalog = Blueprint('sales_catalog', __name__, url_prefix='/sales-catalog')
WEB_CATALOG_SCOPE = 'web_catalog'
WEB_PUBLISHED = 'web_published'
WEB_UNPUBLISHED = 'web_unpublished'
WEB_DRAFT = 'web_draft'


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _to_float(value):
    if value in (None, ''):
        return None
    try:
        return float(value)
    except (TypeError, ValueError, InvalidOperation):
        return None


def _to_int(value, default=None):
    if value in (None, ''):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_bool(value, default=True):
    if value in (None, ''):
        return default
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {'true', '1', 'yes', 'y', 'si', 'sí'}:
        return True
    if normalized in {'false', '0', 'no', 'n'}:
        return False
    return default


def _decimal_or_none(value, field='price'):
    if value in (None, ''):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise AppError('errors.invalid_field', 400, {'field': field})


_image_url = image_url


def _web_status_by_code(session, code: str) -> InventoryStatus:
    status = (
        session.query(InventoryStatus)
        .filter(InventoryStatus.inventory_status_code == code)
        .filter(InventoryStatus.flow_scope == WEB_CATALOG_SCOPE)
        .filter(InventoryStatus.deletion_date.is_(None))
        .first()
    )
    if not status:
        raise AppError('errors.web_catalog_status_missing', 500, {'status': code})
    return status


def _web_status_by_id(session, status_id) -> InventoryStatus:
    status = (
        session.query(InventoryStatus)
        .filter(InventoryStatus.id_inventory_status == status_id)
        .filter(InventoryStatus.flow_scope == WEB_CATALOG_SCOPE)
        .filter(InventoryStatus.deletion_date.is_(None))
        .first()
    )
    if not status:
        raise AppError('errors.invalid_field', 400, {'field': 'id_inventory_status'})
    return status


def _get_product_or_404(session, product_id) -> Product:
    product = (
        session.query(Product)
        .filter(Product.id_product == product_id)
        .filter(Product.deletion_date.is_(None))
        .first()
    )
    if not product:
        raise AppError('errors.not_found', 404, {'entity': 'product', 'id': product_id})
    return product


def _get_or_create_config(session, product_id, user_id=None) -> ProductSaleConfig:
    config = (
        session.query(ProductSaleConfig)
        .filter(ProductSaleConfig.id_product == product_id)
        .filter(ProductSaleConfig.deletion_date.is_(None))
        .first()
    )
    if config:
        return config

    draft_status = _web_status_by_code(session, WEB_DRAFT)
    now = _now()
    config = ProductSaleConfig(
        id_product=product_id,
        margin_percent=Decimal('0'),
        manual_price=None,
        id_inventory_status=draft_status.id_inventory_status,
        is_active=True,
        created_by=user_id or 1,
        creation_date=now,
        last_update_date=now,
    )
    session.add(config)
    session.flush()
    return config


def _config_status(session, config):
    if not config:
        return None
    return (
        session.query(InventoryStatus)
        .filter(InventoryStatus.id_inventory_status == config.id_inventory_status)
        .first()
    )


def _serialize_product_catalog_item(product, config=None, status=None) -> dict:
    pricing = PricingService.calculate_public_price(
        base_price=getattr(product, 'gross_price', None),
        margin_percent=getattr(config, 'margin_percent', None) if config else None,
        manual_price=getattr(config, 'manual_price', None) if config else None,
    )

    return {
        'id_product': product.id_product,
        'product_code': product.product_code,
        'descripcion': product.descripcion,
        'gross_price': _to_float(product.gross_price),
        'cantidad': product.cantidad,
        'stock_available': int(product.cantidad or 0),
        'product_status': product.product_status,
        'path_imagen': product.path_imagen,
        'image_url': _image_url(product.path_imagen),
        'config': None if not config else {
            'id_product_sale_config': config.id_product_sale_config,
            'id_product': config.id_product,
            'margin_percent': _to_float(config.margin_percent),
            'manual_price': _to_float(config.manual_price),
            'id_inventory_status': config.id_inventory_status,
            'is_active': bool(config.is_active),
        },
        'publication_status': None if not status else {
            'id_inventory_status': status.id_inventory_status,
            'inventory_status_code': status.inventory_status_code,
            'inventory_status_description': status.inventory_status_description,
            'color': status.color,
            'flow_scope': status.flow_scope,
        },
        'pricing': pricing,
    }


def _query_catalog_rows(session):
    return (
        session.query(Product, ProductSaleConfig, InventoryStatus)
        .outerjoin(
            ProductSaleConfig,
            and_(
                ProductSaleConfig.id_product == Product.id_product,
                ProductSaleConfig.deletion_date.is_(None),
            ),
        )
        .outerjoin(
            InventoryStatus,
            ProductSaleConfig.id_inventory_status == InventoryStatus.id_inventory_status,
        )
        .filter(Product.deletion_date.is_(None))
    )


@bp_sales_catalog.route('/products', methods=['GET'])
@token_required
@require_entity_permission('product_sale_config', 'read')
def list_sales_catalog_products(user_data):
    search = str(request.args.get('search') or '').strip()
    status_code = str(request.args.get('status') or '').strip()
    configured = str(request.args.get('configured') or '').strip().lower()
    page = max(_to_int(request.args.get('page'), 1), 1)
    per_page = min(max(_to_int(request.args.get('per_page'), 25), 1), 100)

    with transaction_context() as session:
        query = _query_catalog_rows(session)

        if search:
            pattern = f'%{search}%'
            query = query.filter(or_(Product.product_code.ilike(pattern), Product.descripcion.ilike(pattern)))

        if status_code:
            query = query.filter(InventoryStatus.inventory_status_code == status_code)

        if configured == 'true':
            query = query.filter(ProductSaleConfig.id_product_sale_config.isnot(None))
        elif configured == 'false':
            query = query.filter(ProductSaleConfig.id_product_sale_config.is_(None))

        total = query.count()
        rows = (
            query
            .order_by(Product.id_product.asc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        items = [
            _serialize_product_catalog_item(product, config, status)
            for product, config, status in rows
        ]

    return jsonify({'items': items, 'total': total, 'page': page, 'per_page': per_page})


@bp_sales_catalog.route('/products/<int:id_product>/preview-price', methods=['GET'])
@token_required
@require_entity_permission('product_sale_config', 'read')
def preview_product_price(user_data, id_product):
    with transaction_context() as session:
        product = _get_product_or_404(session, id_product)
        config = (
            session.query(ProductSaleConfig)
            .filter(ProductSaleConfig.id_product == id_product)
            .filter(ProductSaleConfig.deletion_date.is_(None))
            .first()
        )
        status = _config_status(session, config)
        item = _serialize_product_catalog_item(product, config, status)
    return jsonify(item)


def _apply_config_payload(session, config, payload):
    if 'margin_percent' in payload:
        config.margin_percent = _decimal_or_none(payload.get('margin_percent'), 'margin_percent')
    if 'manual_price' in payload:
        config.manual_price = _decimal_or_none(payload.get('manual_price'), 'manual_price')
    if 'id_inventory_status' in payload:
        status = _web_status_by_id(session, payload.get('id_inventory_status'))
        config.id_inventory_status = status.id_inventory_status
    elif 'inventory_status_code' in payload:
        status = _web_status_by_code(session, str(payload.get('inventory_status_code') or '').strip())
        config.id_inventory_status = status.id_inventory_status
    if 'is_active' in payload:
        config.is_active = _to_bool(payload.get('is_active'), True)
    config.last_update_date = _now()
    return config


@bp_sales_catalog.route('/products/<int:id_product>/config', methods=['POST', 'PATCH'])
@token_required
@require_entity_permission('product_sale_config', 'update')
def upsert_product_config(user_data, id_product):
    payload = request.get_json() or {}
    with transaction_context() as session:
        product = _get_product_or_404(session, id_product)
        config = _get_or_create_config(session, id_product, user_data.get('id_user'))
        _apply_config_payload(session, config, payload)
        session.flush()
        status = _config_status(session, config)
        item = _serialize_product_catalog_item(product, config, status)
    return jsonify(item)


@bp_sales_catalog.route('/products/bulk-margin', methods=['POST'])
@token_required
@require_entity_permission('product_sale_config', 'update')
def bulk_margin(user_data):
    payload = request.get_json() or {}
    product_ids = payload.get('product_ids') or []
    margin_percent = _decimal_or_none(payload.get('margin_percent'), 'margin_percent')
    if not isinstance(product_ids, list) or not product_ids:
        raise AppError('errors.validation_failed', 400, {'fields': ['product_ids']})

    updated = 0
    with transaction_context() as session:
        for raw_id in product_ids:
            product_id = _to_int(raw_id)
            if not product_id:
                continue
            _get_product_or_404(session, product_id)
            config = _get_or_create_config(session, product_id, user_data.get('id_user'))
            config.margin_percent = margin_percent
            config.last_update_date = _now()
            updated += 1

    return jsonify({'updated': updated})


@bp_sales_catalog.route('/products/bulk-publish', methods=['POST'])
@token_required
@require_entity_permission('product_sale_config', 'update')
def bulk_publish(user_data):
    payload = request.get_json() or {}
    product_ids = payload.get('product_ids') or []
    publish = _to_bool(payload.get('publish'), True)
    target_code = WEB_PUBLISHED if publish else WEB_UNPUBLISHED

    if not isinstance(product_ids, list) or not product_ids:
        raise AppError('errors.validation_failed', 400, {'fields': ['product_ids']})

    updated = 0
    with transaction_context() as session:
        status = _web_status_by_code(session, target_code)
        for raw_id in product_ids:
            product_id = _to_int(raw_id)
            if not product_id:
                continue
            _get_product_or_404(session, product_id)
            config = _get_or_create_config(session, product_id, user_data.get('id_user'))
            config.id_inventory_status = status.id_inventory_status
            config.is_active = True
            config.last_update_date = _now()
            updated += 1

    return jsonify({'updated': updated, 'inventory_status_code': target_code})
