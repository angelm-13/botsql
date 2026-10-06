from __future__ import annotations
import base64
from datetime import datetime
from flask import Blueprint, jsonify, request
from app.services.customer_supplier_service import CustomerSupplierService
from app.utils.auth import token_required, require_entity_permission
from app.utils.errors import AppError
from app.utils.field_access import COLUMNAS_DE_AUDITORIA

bp_customer_supplier = Blueprint('customer_supplier', __name__, url_prefix='/customer_supplier')
ALLOWED_FIELDS = ['id_customer_supplier', 'postal_code', 'name', 'title', 'contact_name', 'phone', 'email', 'web_site', 'street', 'number_ext', 'number_int', 'neighborhood', 'city', 'geographic_state', 'fiscal_type', 'last_fiscal_certification_date', 'tax_id', 'type', 'sla_level', 'credit_limit', 'logistics_notes', 'is_principal', 'csd_status', 'csd_uploaded_at', 'id_user', 'created_by', 'creation_date', 'last_update_date', 'deletion_date', 'path_logo']

TECHNICAL_RESPONSE_FIELDS = {'id_customer_supplier'}
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
            .filter(Field.table_name == 'customer_supplier')
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
    return visible | set(TECHNICAL_RESPONSE_FIELDS) | COLUMNAS_DE_AUDITORIA, writable


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



@bp_customer_supplier.route('/options', methods=['GET'])
@token_required
@require_entity_permission('proyect', 'read')
def list_customer_supplier_options(user_data):
    """Solo id+nombre, para el selector de "Cliente" al crear un proyecto y
    para resolver el nombre del cliente en la lista/tablero de proyectos.

    Deliberadamente NO exige el permiso de lectura completo de
    customer_supplier -- un rol que puede ver/crear proyectos (Supervisor,
    Gerente, Jefe de taller) no necesariamente puede ver el CRM completo.
    Se exige 'read' sobre proyect, no 'create': Gerente (control_type=6,
    LEER|ACTUALIZAR, sin CREAR) autoriza proyectos pero no los crea, y
    necesita el nombre del cliente igual para ver la lista -- con 'create'
    como filtro, este endpoint le daba 403 y el nombre salia "#undefined".
    """
    return jsonify(CustomerSupplierService.options())


@bp_customer_supplier.route('/', methods=['GET'])
@token_required
@require_entity_permission('customer_supplier', 'read')
def list_customer_supplier(user_data):
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    sort = request.args.get('sort')
    filters = {k: v for k, v in request.args.items() if k not in {'page', 'per_page', 'sort', 'q'} and k in ALLOWED_FIELDS}
    return _jsonify_projected_list(user_data, CustomerSupplierService.list(page=page, per_page=per_page, filters=filters, sort=sort, q=request.args.get('q')))


@bp_customer_supplier.route('/<id_customer_supplier>', methods=['GET'])
@token_required
@require_entity_permission('customer_supplier', 'read')
def get_customer_supplier(user_data, id_customer_supplier):
    return _jsonify_projected_record(user_data, CustomerSupplierService.get(id_customer_supplier))


@bp_customer_supplier.route('/', methods=['POST'])
@token_required
@require_entity_permission('customer_supplier', 'create')
def create_customer_supplier(user_data):
    payload = _filter_payload_for_actor(request.get_json() or {}, user_data)
    # `id_user` (vendedor) es NOT NULL pero ya no se captura en el formulario, y a un
    # rol sin permiso de campo sobre el se le filtra del payload: sin esto el alta
    # fallaba pidiendo un vendedor que nadie podia elegir. Por omision, quien captura.
    if not payload.get('id_user'):
        payload['id_user'] = user_data.get('id_user')
    return _jsonify_projected_record(user_data, CustomerSupplierService.create(payload, user_id=user_data.get('id_user')), status=201)


@bp_customer_supplier.route('/<id_customer_supplier>', methods=['PUT'])
@token_required
@require_entity_permission('customer_supplier', 'update')
def update_customer_supplier(user_data, id_customer_supplier):
    payload = _filter_payload_for_actor(request.get_json() or {}, user_data)
    return _jsonify_projected_record(user_data, CustomerSupplierService.update(id_customer_supplier, payload, user_id=user_data.get('id_user')))


@bp_customer_supplier.route('/<id_customer_supplier>', methods=['DELETE'])
@token_required
@require_entity_permission('customer_supplier', 'delete')
def delete_customer_supplier(user_data, id_customer_supplier):
    return jsonify(CustomerSupplierService.delete(id_customer_supplier, user_id=user_data.get('id_user')))


@bp_customer_supplier.route('/<int:id_customer_supplier>/csd', methods=['POST'])
@token_required
def upload_customer_supplier_csd(user_data, id_customer_supplier):
    """Registra el CSD de un emisor en la cuenta multiemisor del PAC.

    Multipart: archivos 'cer' y 'key' + campo 'password'. La llave no se
    guarda en tyakxa -- se manda al PAC, que la custodia (ver
    FacturamaMultiemisorProvider.upload_csd).
    """
    from app.models.customer_supplier import CustomerSupplier
    from app.models.session import transaction_context
    from app.services.stamping import configured_provider
    from app.routes.stamping import _require_admin

    _require_admin(user_data)

    cer = request.files.get('cer')
    key = request.files.get('key')
    password = request.form.get('password', '')
    if not cer or not key:
        raise AppError('customer_supplier.csd_files_missing', 400)

    with transaction_context() as db_session:
        customer_supplier = db_session.get(CustomerSupplier, id_customer_supplier)
        if not customer_supplier:
            raise AppError('errors.resource_not_found', 404)
        if not customer_supplier.tax_id:
            raise AppError('customer_supplier.rfc_missing', 400)

        cer_b64 = base64.b64encode(cer.read()).decode('ascii')
        key_b64 = base64.b64encode(key.read()).decode('ascii')
        ok, message = configured_provider().upload_csd(
            customer_supplier.tax_id, cer_b64, key_b64, password,
        )

        customer_supplier.csd_status = 'uploaded' if ok else 'error'
        customer_supplier.csd_uploaded_at = datetime.utcnow() if ok else None
        db_session.flush()
        record = customer_supplier.serialize()

    return jsonify({'ok': ok, 'message': message, 'data': record}), (200 if ok else 502)
