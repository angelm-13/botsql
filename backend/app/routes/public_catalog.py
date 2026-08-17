from __future__ import annotations
import json
import time
from collections import defaultdict, deque
from urllib.parse import urlparse
from flask import Blueprint, jsonify, request
from sqlalchemy import and_, or_
from app.models import Product, ProductSaleConfig, InventoryStatus, PublicApiKey, ProductFamily, Brand
from app.models.session import transaction_context
from app.services.pricing_service import PricingService
from app.services.public_api_key_manager import PublicApiKeyManager
from app.utils.errors import AppError


bp_public_catalog = Blueprint('public_catalog', __name__, url_prefix='/public')
WEB_CATALOG_SCOPE = 'web_catalog'
WEB_PUBLISHED = 'web_published'
_RATE_LIMIT_WINDOW_SECONDS = 60
_rate_limit_hits = defaultdict(deque)


def _normalize_domain(raw_value: str) -> str:
    text = str(raw_value or '').strip().lower().rstrip('/')
    if not text:
        return ''
    parsed = urlparse(text if '://' in text else '//' + text)
    host = parsed.netloc or parsed.path or ''
    return host.lower().strip().rstrip('/')


def _origin_host() -> str:
    raw = request.headers.get('Origin') or request.headers.get('Referer') or ''
    return _normalize_domain(raw)


def _allowed_domains(raw_value) -> list[str]:
    text = str(raw_value or '').strip()
    if not text:
        return []
    values = []
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            values = parsed
    except Exception:
        values = []
    if not values:
        values = [part for part in text.split(',')]
    return [domain for domain in (_normalize_domain(item) for item in values) if domain]


def _domain_allowed(record: PublicApiKey) -> bool:
    allowed = _allowed_domains(record.allowed_domains)
    if not allowed:
        return True
    host = _origin_host()
    if not host:
        return True
    return any(host == domain or host.endswith('.' + domain) for domain in allowed)


def _default_public_api_rate_limit() -> int:
    try:
        return max(int(os.getenv('PUBLIC_API_RATE_LIMIT_DEFAULT', '60')), 1)
    except (TypeError, ValueError):
        return 60


def _check_rate_limit(record: PublicApiKey) -> None:
    limit = int(record.rate_limit_per_min or _default_public_api_rate_limit())
    if limit <= 0:
        limit = _default_public_api_rate_limit()
    now = time.time()
    bucket_key = record.key_prefix or str(record.id_public_api_key)
    hits = _rate_limit_hits[bucket_key]
    while hits and now - hits[0] >= _RATE_LIMIT_WINDOW_SECONDS:
        hits.popleft()
    if len(hits) >= limit:
        raise AppError('errors.rate_limit_exceeded', 429)
    hits.append(now)


def _require_public_api_key() -> PublicApiKey:
    plain_key = request.headers.get('X-API-Key') or ''
    if not plain_key:
        raise AppError('errors.auth_required', 401)

    prefix = plain_key[:PublicApiKeyManager.PREFIX_LENGTH]
    with transaction_context() as session:
        candidates = (
            session.query(PublicApiKey)
            .filter(PublicApiKey.key_prefix == prefix)
            .filter(PublicApiKey.is_active.is_(True))
            .filter(PublicApiKey.deletion_date.is_(None))
            .all()
        )
        for record in candidates:
            if not PublicApiKeyManager.verify_key(plain_key, record.key_hash):
                continue
            if not _domain_allowed(record):
                raise AppError('errors.permission_denied', 403, {'reason': 'domain_not_allowed'})
            _check_rate_limit(record)
            record.last_used_at = PublicApiKeyManager._now()
            session.flush()
            return record

    raise AppError('errors.invalid_token', 401)


def _to_int(value, default=None):
    if value in (None, ''):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _public_base_url():
    return (request.host_url or '').rstrip('/')


def _image_url(path_value):
    raw = str(path_value or '').strip()
    if not raw:
        return ''
    if raw.startswith(('http://', 'https://')):
        return raw
    return _public_base_url() + '/' + raw.lstrip('/')


def _has_public_price(config) -> bool:
    return getattr(config, 'manual_price', None) not in (None, '') or getattr(config, 'margin_percent', None) not in (None, '')


def _serialize_public_product(product, config, status, family=None, brand=None) -> dict:
    pricing = PricingService.calculate_public_price(
        base_price=getattr(product, 'gross_price', None),
        margin_percent=getattr(config, 'margin_percent', None),
        manual_price=getattr(config, 'manual_price', None),
    )
    return {
        'id': product.id_product,
        'sku': product.product_code,
        'name': product.descripcion,
        'description': product.note,
        'category': None if not family else {
            'id': family.id_product_family,
            'name': family.product_family_description,
        },
        'brand': None if not brand else {
            'id': brand.id_brand,
            'name': brand.brand_description,
        },
        'image_url': _image_url(product.path_imagen),
        'stock_available': int(product.cantidad or 0),
        'price': pricing.get('public_price'),
        'currency': 'MXN',
        'tax_included': True,
    }


def _public_products_query(session):
    return (
        session.query(Product, ProductSaleConfig, InventoryStatus, ProductFamily, Brand)
        .join(ProductSaleConfig, and_(
            ProductSaleConfig.id_product == Product.id_product,
            ProductSaleConfig.deletion_date.is_(None),
            ProductSaleConfig.is_active.is_(True),
            or_(ProductSaleConfig.manual_price.isnot(None), ProductSaleConfig.margin_percent.isnot(None)),
        ))
        .join(InventoryStatus, and_(
            InventoryStatus.id_inventory_status == ProductSaleConfig.id_inventory_status,
            InventoryStatus.flow_scope == WEB_CATALOG_SCOPE,
            InventoryStatus.inventory_status_code == WEB_PUBLISHED,
            InventoryStatus.deletion_date.is_(None),
        ))
        .outerjoin(ProductFamily, ProductFamily.id_product_family == Product.id_familia)
        .outerjoin(Brand, Brand.id_brand == Product.id_marca)
        .filter(Product.deletion_date.is_(None))
        .filter(Product.cantidad > 0)
    )


def _apply_public_filters(query):
    search = str(request.args.get('search') or '').strip()
    category_id = _to_int(request.args.get('category_id'))
    if search:
        pattern = f'%{search}%'
        query = query.filter(or_(Product.product_code.ilike(pattern), Product.descripcion.ilike(pattern), Product.note.ilike(pattern)))
    if category_id:
        query = query.filter(Product.id_familia == category_id)
    return query


@bp_public_catalog.route('/health', methods=['GET'])
def public_health():
    return jsonify({'status': 'ok', 'service': 'public_catalog'})


@bp_public_catalog.route('/products', methods=['GET'])
def public_products():
    _require_public_api_key()
    page = max(_to_int(request.args.get('page'), 1), 1)
    per_page = min(max(_to_int(request.args.get('per_page'), 20), 1), 100)
    with transaction_context() as session:
        query = _apply_public_filters(_public_products_query(session))
        total = query.count()
        rows = (
            query
            .order_by(Product.id_product.asc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        items = [
            _serialize_public_product(product, config, status, family, brand)
            for product, config, status, family, brand in rows
            if _has_public_price(config)
        ]
    return jsonify({'items': items, 'total': total, 'page': page, 'per_page': per_page})


@bp_public_catalog.route('/products/<int:id_product>', methods=['GET'])
def public_product_detail(id_product):
    _require_public_api_key()
    with transaction_context() as session:
        row = (
            _public_products_query(session)
            .filter(Product.id_product == id_product)
            .first()
        )
        if not row:
            raise AppError('errors.not_found', 404, {'entity': 'product', 'id': id_product})
        product, config, status, family, brand = row
        if not _has_public_price(config):
            raise AppError('errors.not_found', 404, {'entity': 'product', 'id': id_product})
        item = _serialize_public_product(product, config, status, family, brand)
    return jsonify(item)


@bp_public_catalog.route('/categories', methods=['GET'])
def public_categories():
    _require_public_api_key()
    with transaction_context() as session:
        rows = (
            _public_products_query(session)
            .filter(ProductFamily.id_product_family.isnot(None))
            .with_entities(ProductFamily)
            .distinct()
            .order_by(ProductFamily.id_product_family.asc())
            .all()
        )
        items = [
            {
                'id': row.id_product_family,
                'name': row.product_family_description,
                'type': row.type,
            }
            for row in rows
        ]
    return jsonify({'items': items, 'total': len(items)})
