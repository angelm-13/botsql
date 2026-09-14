from __future__ import annotations
from functools import wraps
from flask import jsonify, request
import jwt
import os

PERMISSION_BITS = {'create': 1, 'read': 2, 'update': 4, 'delete': 8}
SECRET_KEY = os.getenv('JWT_SECRET', 'dev-secret-change-me')
PUBLIC_JWT_SCOPE = os.getenv('PUBLIC_JWT_SCOPE', 'web_shopper')
BOOTSTRAP_ONLY_ENTITIES = {'event_log', 'user_mfa', 'password_reset_token'}
ADMIN_PERMISSION_ENTITIES = {'permission', 'entity_permission', 'nm_field_permission', 'field'}
ADMIN_PERMISSION_READ_ENTITIES = ADMIN_PERMISSION_ENTITIES | {'user', 'department', 'subdepartment', 'level'}


def token_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'error_key': 'errors.auth_required'}), 401
        try:
            user_data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        except Exception:
            return jsonify({'error_key': 'errors.invalid_token'}), 401
        if str(user_data.get('scope') or '').strip().lower() == str(PUBLIC_JWT_SCOPE).strip().lower():
            return jsonify({'error_key': 'errors.invalid_token'}), 401
        return fn(user_data, *args, **kwargs)
    return wrapper


def _is_superuser(user_data: dict) -> bool:
    return bool(user_data.get('is_superuser') or user_data.get('is_bootstrap_admin'))


def _get_permission_id(user_data: dict):
    value = user_data.get('id_permission') or user_data.get('permission_id')
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _plan_permite(entity_name: str) -> bool:
    """Si el modulo de esta entidad esta en el plan del despliegue.

    Es la capa de arriba: el plan dice que modulos existen aqui, el rol dice
    quien puede usarlos. Se comprueba antes que el rol porque una entidad fuera
    del plan no deberia poder concederse siquiera, y este es el punto por donde
    ya pasa cada ruta protegida.

    Se aplica tambien al superusuario. Podria parecer excesivo, pero el plan no
    es un permiso: es lo que el cliente compro. Un modulo fuera del plan no
    existe en este despliegue para nadie, y dejarselo al administrador seria
    dejar una puerta que se abre concediendose un rol.
    """
    from app.modules.plan import entidad_habilitada

    return entidad_habilitada(entity_name)


def _has_entity_permission(user_data: dict, entity_name: str, action: str) -> bool:
    # El plan primero: sin el modulo comprado, no hay rol que valga.
    if not _plan_permite(entity_name):
        return False

    if _is_superuser(user_data):
        return True

    if entity_name in BOOTSTRAP_ONLY_ENTITIES:
        return False

    bit = PERMISSION_BITS.get(action)
    if bit is None:
        return False

    permission_id = _get_permission_id(user_data)
    if not permission_id:
        return False

    from app.models.entity_permission import EntityPermission
    from app.models.session import transaction_context

    with transaction_context() as db_session:
        record = (
            db_session.query(EntityPermission)
            .filter(EntityPermission.id_permission == permission_id)
            .filter(EntityPermission.entity_name == entity_name)
            .filter(EntityPermission.deletion_date.is_(None))
            .first()
        )
        if not record:
            return False
        try:
            control_type = int(record.control_type)
        except (TypeError, ValueError):
            return False
        return (control_type & bit) == bit


def has_kpi_permission(session, user_data: dict, id_kpi_definition, action: str = 'read') -> bool:
    """Si el actor puede usar este KPI puntual.

    Dos capas, igual que `_has_entity_permission`, pero la primera mira el
    modulo DEL KPI (`kpi_definition.modulo`, ej. "facturacion"), no el modulo
    "kpis" del registro: un cliente puede tener "kpis" contratado sin tener
    "facturacion", y en ese caso sus KPIs de facturacion no existen para
    nadie, con independencia del rol. `require_entity_permission('kpi_definition',
    ...)` ya cubre el guardia de modulo "kpis"; este es el guardia del modulo
    que el KPI mide.

    `session` viaja como parametro en vez de abrir su propia transaccion
    porque quien llama (la ruta) ya tiene una abierta para resolver el resto
    de la peticion.
    """
    from app.models.kpi_definition import KpiDefinition
    from app.models.nm_permission_kpi import NmPermissionKpi
    from app.modules.plan import modulo_habilitado

    kpi = session.get(KpiDefinition, id_kpi_definition)
    if kpi is None:
        return False
    if not modulo_habilitado(kpi.modulo):
        return False

    if _is_superuser(user_data):
        return True

    bit = PERMISSION_BITS.get(action)
    if bit is None:
        return False

    permission_id = _get_permission_id(user_data)
    if not permission_id:
        return False

    record = (
        session.query(NmPermissionKpi)
        .filter(NmPermissionKpi.id_permission == permission_id)
        .filter(NmPermissionKpi.id_kpi_definition == id_kpi_definition)
        .filter(NmPermissionKpi.deletion_date.is_(None))
        .first()
    )
    if not record:
        return False
    try:
        control_type = int(record.control_type)
    except (TypeError, ValueError):
        return False
    return (control_type & bit) == bit


def require_entity_permission(entity_name: str, action: str):
    def decorator(fn):
        @wraps(fn)
        def wrapper(user_data, *args, **kwargs):
            if not _plan_permite(entity_name):
                return jsonify({
                    'error_key': 'errors.module_not_in_plan',
                    'meta': {'entity': entity_name},
                }), 403
            if not _has_entity_permission(user_data, entity_name, action):
                return jsonify({'error_key': 'errors.permission_denied', 'meta': {'entity': entity_name, 'action': action}}), 403
            return fn(user_data, *args, **kwargs)
        return wrapper
    return decorator
