from __future__ import annotations
from copy import deepcopy
from flask import Blueprint, jsonify
from app.utils.auth import _has_entity_permission, token_required

bp_security = Blueprint('security', __name__, url_prefix='/security')

# El catalogo se arma una vez por proceso y se sirve en copia.
#
# Antes era un JSON de ~8700 lineas escrito aqui mismo, congelado contra un
# esquema que ya no es el de hoy: le faltaban 34 de las 85 entidades del
# registro -logistica entera, documentos, laboratorio, KPIs- y a otras 14 les
# faltaban columnas que la tabla si tiene. Ver `app/modules/catalogo.py`.
_CATALOGO = None


def _catalogo_base() -> dict:
    global _CATALOGO
    if _CATALOGO is None:
        from app.modules.catalogo import catalogo_base
        _CATALOGO = catalogo_base()
    return _CATALOGO



def _is_admin_actor(user_data: dict) -> bool:
    """Quien puede abrir el gestor de roles: el que tiene `entity_permission` (Gestor)
    o el superusuario. Antes bastaba con ser cuenta de tipo admin, que no es el rol."""
    return _has_entity_permission(user_data, 'entity_permission', 'read')


def _catalog_for_actor(user_data: dict) -> dict:
    """Lo que el gestor de roles puede ofrecer para conceder.

    Tres cosas que este catalogo tiene que respetar:

    **Las entidades y las capacidades salen del registro, no de una lista
    aqui.** Las capacidades estaban escritas a mano y eran cinco de las
    dieciseis que existen, asi que las del punto de venta no se podian conceder
    desde la interfaz; las entidades venian de un JSON congelado que cubria 51
    de las 85 del registro, y logistica entera -21 tablas-, documentos,
    laboratorio y KPIs no aparecian en la pantalla. Una lista duplicada del
    registro se queda corta en cuanto alguien agrega algo y no se acuerda de
    este archivo. Ahora se deriva: ver `app/modules/catalogo.py`.

    **El plan del despliegue recorta el catalogo.** Es lo que hace del plan un
    techo de verdad: el administrador del cliente reparte permisos con libertad,
    pero solo entre los modulos que compro. Sin este filtro el gestor mentiria
    -concedes logistica, lo ves guardado, y el usuario recibe 403 al entrar-, y
    eso es peor que no ofrecerla: manda a buscar el problema en el rol, donde no
    hay nada que arreglar.

    **Lo que solo toca la cuenta de arranque no se ofrece a nadie mas.** Son
    `event_log`, `user_mfa` y `password_reset_token`: conceder una fila que el
    codigo va a rechazar de todas formas solo sirve para confundir.
    """
    from app.modules.plan import entidad_habilitada

    catalog = deepcopy(_catalogo_base())
    if not (user_data.get('is_superuser') or user_data.get('is_bootstrap_admin')):
        catalog['entities'] = [
            entity for entity in catalog.get('entities', [])
            if not entity.get('is_bootstrap_only')
        ]
    catalog['entities'] = [
        entity for entity in catalog.get('entities', [])
        if entidad_habilitada(entity.get('entity_name'))
    ]
    return catalog


@bp_security.route('/permission-catalog', methods=['GET'])
@token_required
def permission_catalog(user_data):
    if not _is_admin_actor(user_data):
        return jsonify({'error_key': 'errors.permission_denied', 'meta': {'resource': 'permission_catalog'}}), 403
    return jsonify(_catalog_for_actor(user_data))


def _safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


@bp_security.route('/storage', methods=['GET'])
@token_required
def deployment_storage(user_data):
    """Cuanto espacio llevan los archivos y cuanto permite el plan.

    Se expone a cualquier usuario autenticado: el cliente tiene derecho a saber
    cuanto lleva usado de lo que pago, y avisar antes de llegar al tope es lo
    unico que evita que una subida falle sin previo aviso.
    """
    from flask import request

    from app.services.storage_service import estado

    refrescar = str(request.args.get('refresh') or '').strip().lower() in {'1', 'true', 'si'}
    return jsonify(estado(refrescar=refrescar))


@bp_security.route('/plan', methods=['GET'])
@token_required
def deployment_plan(user_data):
    """El plan de este despliegue: que modulos compro el cliente y sus topes.

    Se expone para que la aplicacion pueda decir "esto no esta en tu plan" en
    vez de ensenar una pantalla que responde 403, y para que la administracion
    sepa contra que topes esta trabajando. No lleva nada secreto: el cliente
    tiene derecho a ver que compro.
    """
    from app.modules.plan import plan_actual

    return jsonify(plan_actual().serialize())


@bp_security.route('/my-permissions', methods=['GET'])
@token_required
def my_permissions(user_data):
    permission_id = _safe_int(user_data.get('id_permission') or user_data.get('permission_id'))
    if not permission_id:
        return jsonify({'entity_permissions': [], 'field_permissions': [], 'fields': []})

    from app.models.session import transaction_context
    from app.models.permission import Permission
    from app.models.entity_permission import EntityPermission
    from app.models.nm_field_permission import NmFieldPermission
    from app.models.field import Field

    with transaction_context() as db_session:
        permission = (
            db_session.query(Permission)
            .filter(Permission.id_permission == permission_id)
            .filter(Permission.deletion_date.is_(None))
            .first()
        )
        if not permission:
            return jsonify({'entity_permissions': [], 'field_permissions': [], 'fields': []})

        entity_rows = (
            db_session.query(EntityPermission)
            .filter(EntityPermission.id_permission == permission_id)
            .filter(EntityPermission.deletion_date.is_(None))
            .all()
        )
        # El plan filtra lo que se devuelve, y no solo lo que se puede usar.
        # De estas filas sale el menu: si pasaran las de un modulo que el
        # cliente no compro, veria las pantallas y recibiria un 403 al entrar.
        # Un menu que lleva a puertas cerradas es peor que uno mas corto.
        from app.modules.plan import entidad_habilitada
        entity_rows = [
            fila for fila in entity_rows
            if entidad_habilitada(getattr(fila, 'entity_name', None))
        ]
        field_permission_rows = (
            db_session.query(NmFieldPermission)
            .filter(NmFieldPermission.id_permission == permission_id)
            .filter(NmFieldPermission.deletion_date.is_(None))
            .all()
        )
        field_ids = [row.id_field for row in field_permission_rows if row.id_field is not None]
        field_rows = []
        if field_ids:
            field_rows = (
                db_session.query(Field)
                .filter(Field.id_field.in_(field_ids))
                .filter(Field.deletion_date.is_(None))
                .all()
            )
        field_by_id = {row.id_field: row for row in field_rows}

        entity_permissions = []
        for row in entity_rows:
            entity_permissions.append({
                'id_entity_permission': row.id_entity_permission,
                'id_permission': row.id_permission,
                'entity_name': row.entity_name,
                'scope_create': row.scope_create,
                'scope_read': row.scope_read,
                'scope_update': row.scope_update,
                'scope_delete': row.scope_delete,
                'menu_location': row.menu_location,
                'menu_group': row.menu_group,
                'menu_group_icon': row.menu_group_icon,
                'menu_label': row.menu_label,
                'menu_order': row.menu_order,
            })

        field_permissions = []
        for row in field_permission_rows:
            field = field_by_id.get(row.id_field)
            payload = {
                'id_nm_field_permission': row.id_nm_field_permission,
                'id_permission': row.id_permission,
                'id_field': row.id_field,
                'control_type': row.control_type,
            }
            if field:
                payload['table_name'] = field.table_name
                payload['entity_name'] = field.table_name
                payload['field_name'] = field.field_name
            field_permissions.append(payload)

        fields = [{
            'id_field': row.id_field,
            'table_name': row.table_name,
            'field_name': row.field_name,
        } for row in field_rows]

        return jsonify({
            'id_permission': permission_id,
            'entity_permissions': entity_permissions,
            'field_permissions': field_permissions,
            'fields': fields,
        })

