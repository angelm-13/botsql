from __future__ import annotations
from flask import Blueprint, jsonify, request
from app.services.nm_incident_product_service import NmIncidentProductService
from app.utils.auth import token_required, require_entity_permission
from app.utils.errors import AppError
from app.utils.field_access import COLUMNAS_DE_AUDITORIA

bp_nm_incident_product = Blueprint('nm_incident_product', __name__, url_prefix='/nm_incident_product')
ALLOWED_FIELDS = ['id_nm_incident_product', 'id_incident', 'id_product', 'note', 'quantity', 'close_date', 'created_by', 'creation_date', 'last_update_date', 'deletion_date']

TECHNICAL_RESPONSE_FIELDS = {'id_nm_incident_product'}
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
            .filter(Field.table_name == 'nm_incident_product')
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



def _require_incident_scope(id_nm_incident_product, user_data):
    """Alcance de un renglon de productos de una incidencia.

    `incident` devuelve 404 a quien no participa, con el criterio de que
    tampoco debe enterarse de que la incidencia existe. Estos renglones cuelgan
    de una incidencia por `id_incident` y no comprobaban nada, asi que se podia
    leer que productos se vieron afectados en cualquier incidencia pidiendo el
    renglon por su id. La incidencia quedaba cerrada y su contenido abierto.
    """
    from app.services.incident_service import require_incident_access

    registro = NmIncidentProductService.get(id_nm_incident_product)
    require_incident_access(registro.get('id_incident'), user_data)
    return registro


@bp_nm_incident_product.route('/', methods=['GET'])
@token_required
@require_entity_permission('nm_incident_product', 'read')
def list_nm_incident_product(user_data):
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    sort = request.args.get('sort')
    filters = {k: v for k, v in request.args.items() if k not in {'page', 'per_page', 'sort', 'q'} and k in ALLOWED_FIELDS}
    from sqlalchemy import func as sql_func
    from app.models import Incident, NmIncidentProduct
    from app.models.session import transaction_context
    from app.services.incident_service import scoped_incident_query

    # Se filtra por las incidencias que el actor puede ver, en lugar de
    # devolverlas todas. Sin esto el listado entregaba los productos afectados
    # en incidencias ajenas, justo lo que `incident` se cuida de no revelar.
    with transaction_context() as db:
        visibles = [
            fila[0] for fila in
            scoped_incident_query(db, user_data).with_entities(Incident.id_incident).all()
        ]
        if not visibles:
            payload = {'items': [], 'total': 0, 'page': page, 'per_page': per_page, 'pages': 0}
            return _jsonify_projected_list(user_data, payload)

        query = db.query(NmIncidentProduct).filter(
            NmIncidentProduct.deletion_date.is_(None),
            NmIncidentProduct.id_incident.in_(visibles),
        )
        for clave, valor in filters.items():
            if hasattr(NmIncidentProduct, clave) and valor not in (None, ''):
                query = query.filter(getattr(NmIncidentProduct, clave) == valor)
        total = query.with_entities(sql_func.count()).scalar() or 0
        renglones = (query.order_by(NmIncidentProduct.id_nm_incident_product)
                     .offset((page - 1) * per_page).limit(per_page).all())
        payload = {
            'items': [r.serialize() for r in renglones],
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page,
        }
    return _jsonify_projected_list(user_data, payload)


@bp_nm_incident_product.route('/<id_nm_incident_product>', methods=['GET'])
@token_required
@require_entity_permission('nm_incident_product', 'read')
def get_nm_incident_product(user_data, id_nm_incident_product):
    return _jsonify_projected_record(user_data, _require_incident_scope(id_nm_incident_product, user_data))


@bp_nm_incident_product.route('/', methods=['POST'])
@token_required
@require_entity_permission('nm_incident_product', 'create')
def create_nm_incident_product(user_data):
    from app.services.incident_service import require_incident_access

    payload = _filter_payload_for_actor(request.get_json() or {}, user_data)
    require_incident_access(payload.get('id_incident'), user_data)
    return _jsonify_projected_record(user_data, NmIncidentProductService.create(payload, user_id=user_data.get('id_user')), status=201)


@bp_nm_incident_product.route('/<id_nm_incident_product>', methods=['PUT'])
@token_required
@require_entity_permission('nm_incident_product', 'update')
def update_nm_incident_product(user_data, id_nm_incident_product):
    from app.services.incident_service import require_incident_access

    payload = _filter_payload_for_actor(request.get_json() or {}, user_data)
    _require_incident_scope(id_nm_incident_product, user_data)
    if payload.get('id_incident') is not None:
        require_incident_access(payload.get('id_incident'), user_data)
    return _jsonify_projected_record(user_data, NmIncidentProductService.update(id_nm_incident_product, payload, user_id=user_data.get('id_user')))


@bp_nm_incident_product.route('/<id_nm_incident_product>', methods=['DELETE'])
@token_required
@require_entity_permission('nm_incident_product', 'delete')
def delete_nm_incident_product(user_data, id_nm_incident_product):
    _require_incident_scope(id_nm_incident_product, user_data)
    return jsonify(NmIncidentProductService.delete(id_nm_incident_product, user_id=user_data.get('id_user')))
