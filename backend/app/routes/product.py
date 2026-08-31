from __future__ import annotations
from flask import Blueprint, jsonify, request
from app.services.product_service import ProductService
from app.services.inventory_service import (
    apply_inventory_movement,
    list_inventory_movements,
    product_stock,
    reconcile_product_stock,
    transfer_inventory,
    warehouse_stock,
)
from app.utils.auth import token_required, require_entity_permission
from app.utils.errors import AppError
import os
from pathlib import Path
from werkzeug.utils import secure_filename


bp_product = Blueprint('product', __name__, url_prefix='/product')
ALLOWED_FIELDS = ['id_product', 'id_invoice', 'id_location', 'id_material', 'gross_price', 'color', 'is_directly_related_to_product_service', 'product_status', 'path_imagen', 'product_code', 'note', 'created_by', 'creation_date', 'last_update_date', 'deletion_date', 'descripcion', 'cantidad', 'id_material', 'id_marca', 'id_familia']

TECHNICAL_RESPONSE_FIELDS = {'id_product'}
FIELD_READ_BIT = 2
# Escribir un campo exige el bit de alta o el de actualizacion, no el de
# lectura. Sin esta distincion no se podia conceder "ver pero no editar".
FIELD_WRITE_BITS = 1 | 4


def _actor_has_unrestricted_field_access(user_data: dict) -> bool:
    return bool(
        user_data.get('is_superuser')
        or user_data.get('is_bootstrap_admin')
        or user_data.get('user_type') == 'admin'
    )


def _safe_int_value(value):
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _field_sets_for_actor(user_data: dict) -> tuple[set[str], set[str]]:
    """Campos que el actor puede ver y campos que puede escribir."""
    if _actor_has_unrestricted_field_access(user_data):
        return set(ALLOWED_FIELDS), set(ALLOWED_FIELDS)

    permission_id = _safe_int_value(user_data.get('id_permission') or user_data.get('permission_id'))
    if not permission_id:
        return set(TECHNICAL_RESPONSE_FIELDS), set()

    from app.models.field import Field
    from app.models.nm_field_permission import NmFieldPermission
    from app.models.session import transaction_context

    visible = set()
    writable = set()
    with transaction_context() as db_session:
        rows = (
            db_session.query(NmFieldPermission, Field)
            .join(Field, NmFieldPermission.id_field == Field.id_field)
            .filter(NmFieldPermission.id_permission == permission_id)
            .filter(NmFieldPermission.deletion_date.is_(None))
            .filter(Field.table_name == 'product')
            .filter(Field.deletion_date.is_(None))
            .all()
        )
        for permission_row, field_row in rows:
            try:
                control_type = int(permission_row.control_type)
            except (TypeError, ValueError):
                continue
            if (control_type & FIELD_READ_BIT) == FIELD_READ_BIT:
                visible.add(field_row.field_name)
            if control_type & FIELD_WRITE_BITS:
                writable.add(field_row.field_name)

    # La llave primaria puede viajar en la respuesta para navegacion interna,
    # acciones de fila y rutas REST, aunque el frontend no la pinte si no fue
    # marcada como visible en el gestor.
    return visible | set(TECHNICAL_RESPONSE_FIELDS), writable


def _visible_response_fields_for_actor(user_data: dict) -> set[str]:
    return _field_sets_for_actor(user_data)[0]


def _writable_request_fields_for_actor(user_data: dict) -> set[str]:
    return _field_sets_for_actor(user_data)[1]


def _filter_payload_for_actor(payload: dict, user_data: dict) -> dict:
    payload = dict(payload or {})
    if _actor_has_unrestricted_field_access(user_data):
        return payload
    writable_fields = _writable_request_fields_for_actor(user_data) - set(TECHNICAL_RESPONSE_FIELDS)
    return {key: value for key, value in payload.items() if key in writable_fields}


def _project_record_payload(record: dict | None, visible_fields: set[str]) -> dict | None:
    if record is None:
        return record
    return {key: value for key, value in dict(record).items() if key in visible_fields}


def _project_list_payload(payload: dict, visible_fields: set[str]) -> dict:
    result = dict(payload or {})
    result['items'] = [
        _project_record_payload(item, visible_fields)
        for item in result.get('items', [])
    ]
    return result


def _jsonify_projected_record(user_data: dict, record: dict | None, status: int | None = None):
    payload = _project_record_payload(record, _visible_response_fields_for_actor(user_data))
    response = jsonify(payload)
    return (response, status) if status is not None else response


def _jsonify_projected_list(user_data: dict, payload: dict):
    return jsonify(_project_list_payload(payload, _visible_response_fields_for_actor(user_data)))



_ALLOWED_PRODUCT_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}
_PRODUCT_IMAGE_MAX_BYTES = 5 * 1024 * 1024


def _product_upload_dir():
    configured_root = os.getenv('UPLOAD_ROOT')
    root = Path(configured_root) if configured_root else Path(__file__).resolve().parents[3] / 'uploads'
    upload_dir = root / 'products'
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def _allowed_image_extension(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in _ALLOWED_PRODUCT_IMAGE_EXTENSIONS


def _safe_product_image_filename(product_id, original_filename):
    safe_original = secure_filename(original_filename or '')
    if not _allowed_image_extension(safe_original):
        raise AppError('errors.invalid_image_type', 400, {'allowed': sorted(_ALLOWED_PRODUCT_IMAGE_EXTENSIONS)})
    extension = safe_original.rsplit('.', 1)[1].lower()
    return f'p_{product_id}.{extension}'


def _delete_previous_product_images(product_id, keep_filename=None):
    prefix = f'p_{product_id}.'
    for candidate in _product_upload_dir().glob(f'{prefix}*'):
        if keep_filename and candidate.name == keep_filename:
            continue
        try:
            candidate.unlink()
        except OSError:
            pass


def _relative_product_image_path(filename):
    return f'uploads/products/{filename}'


@bp_product.route('/', methods=['GET'])
@token_required
@require_entity_permission('product', 'read')
def list_product(user_data):
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    sort = request.args.get('sort')
    filters = {k: v for k, v in request.args.items() if k not in {'page', 'per_page', 'sort'} and k in ALLOWED_FIELDS}
    return _jsonify_projected_list(user_data, ProductService.list_scoped(user_data, page=page, per_page=per_page, filters=filters, sort=sort))


@bp_product.route('/<id_product>', methods=['GET'])
@token_required
@require_entity_permission('product', 'read')
def get_product(user_data, id_product):
    ProductService.require_record_scope(id_product, user_data)
    return _jsonify_projected_record(user_data, ProductService.get(id_product))


@bp_product.route('/', methods=['POST'])
@token_required
@require_entity_permission('product', 'create')
def create_product(user_data):
    payload = _filter_payload_for_actor(request.get_json() or {}, user_data)
    ProductService.require_invoice_scope(payload.get('id_invoice'), user_data)
    return _jsonify_projected_record(user_data, ProductService.create(payload, user_id=user_data.get('id_user')), status=201)


@bp_product.route('/<id_product>', methods=['PUT'])
@token_required
@require_entity_permission('product', 'update')
def update_product(user_data, id_product):
    payload = _filter_payload_for_actor(request.get_json() or {}, user_data)
    ProductService.require_record_scope(id_product, user_data)
    if 'id_invoice' in payload:
        ProductService.require_invoice_scope(payload.get('id_invoice'), user_data)
    return _jsonify_projected_record(user_data, ProductService.update(id_product, payload, user_id=user_data.get('id_user')))


@bp_product.route('/<id_product>/inventory-movements', methods=['POST'])
@token_required
@require_entity_permission('product', 'update')
def create_inventory_movement(user_data, id_product):
    ProductService.require_record_scope(id_product, user_data)
    movement, created = apply_inventory_movement(id_product, request.get_json() or {}, user_data)
    return jsonify({'movement': movement, 'idempotent_replay': not created}), (201 if created else 200)


@bp_product.route('/<id_product>/inventory-movements', methods=['GET'])
@token_required
@require_entity_permission('product', 'read')
def read_inventory_movements(user_data, id_product):
    """Historial del libro de inventario para auditar como llego el saldo."""
    ProductService.require_record_scope(id_product, user_data)
    return jsonify(list_inventory_movements(
        id_product,
        user_data,
        page=request.args.get('page', 1),
        per_page=request.args.get('per_page', 50),
        movement_type=request.args.get('movement_type'),
        location_id=request.args.get('id_location'),
    ))


@bp_product.route('/<id_product>/inventory-reconciliation', methods=['GET'])
@token_required
@require_entity_permission('product', 'read')
def read_inventory_reconciliation(user_data, id_product):
    """Comprueba que el saldo del producto cuadre con la suma del libro."""
    ProductService.require_record_scope(id_product, user_data)
    return jsonify(reconcile_product_stock(id_product, user_data))


@bp_product.route('/<id_product>/inventory-transfers', methods=['POST'])
@token_required
@require_entity_permission('product', 'update')
def create_inventory_transfer(user_data, id_product):
    """Traspasa existencia entre ubicaciones o almacenes en una sola operacion."""
    ProductService.require_record_scope(id_product, user_data)
    result, created = transfer_inventory(id_product, request.get_json() or {}, user_data)
    return jsonify({**result, 'idempotent_replay': not created}), (201 if created else 200)


@bp_product.route('/<id_product>/inventory-stock', methods=['GET'])
@token_required
@require_entity_permission('product', 'read')
def read_product_stock(user_data, id_product):
    """En que ubicaciones y almacenes esta repartido el producto."""
    ProductService.require_record_scope(id_product, user_data)
    return jsonify(product_stock(id_product, user_data))


@bp_product.route('/<id_product>', methods=['DELETE'])
@token_required
@require_entity_permission('product', 'delete')
def delete_product(user_data, id_product):
    ProductService.require_record_scope(id_product, user_data)
    return jsonify(ProductService.delete(id_product, user_id=user_data.get('id_user')))


@bp_product.route('/<id_product>/image', methods=['POST'])
@token_required
@require_entity_permission('product', 'update')
def upload_product_image(user_data, id_product):
    ProductService.require_record_scope(id_product, user_data)
    if request.content_length and request.content_length > _PRODUCT_IMAGE_MAX_BYTES:
        raise AppError('errors.image_too_large', 413, {'max_mb': 5})
    if 'file' not in request.files:
        raise AppError('errors.image_required', 400)
    file = request.files['file']
    if not file or not file.filename:
        raise AppError('errors.image_required', 400)
    filename = _safe_product_image_filename(id_product, file.filename)
    upload_dir = _product_upload_dir()
    target_path = upload_dir / filename
    file.save(target_path)
    relative_path = _relative_product_image_path(filename)
    payload = _filter_payload_for_actor({'path_imagen': relative_path}, user_data)
    if 'path_imagen' not in payload:
        try:
            target_path.unlink()
        except OSError:
            pass
        raise AppError('errors.forbidden', 403)
    updated = ProductService.update(id_product, payload, user_id=user_data.get('id_user'))
    _delete_previous_product_images(id_product, keep_filename=filename)
    return _jsonify_projected_record(user_data, updated)
