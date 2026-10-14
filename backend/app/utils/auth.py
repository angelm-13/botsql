from __future__ import annotations
from functools import wraps
from flask import jsonify, request
import jwt
import os

# Cada accion vive en su propia columna de alcance (0 Sin acceso, 1 Propios,
# 2 Mis grupos, 4 Todos -- ver entity_permission.py). El gate de aqui sigue
# siendo booleano: 0 deniega, cualquier otro valor permite. El alcance real
# (que Propios/Mis grupos filtren de verdad lo que se ve) no esta conectado
# todavia -- ver ARQUITECTURA_TYAKXA_TNY.md.
PERMISSION_SCOPE_COLUMNS = {'create': 'scope_create', 'read': 'scope_read', 'update': 'scope_update', 'delete': 'scope_delete'}
SECRET_KEY = os.getenv('JWT_SECRET', 'dev-secret-change-me')
PUBLIC_JWT_SCOPE = os.getenv('PUBLIC_JWT_SCOPE', 'web_shopper')
BOOTSTRAP_ONLY_ENTITIES = {'event_log', 'user_mfa', 'password_reset_token'}
ADMIN_PERMISSION_ENTITIES = {'permission', 'entity_permission', 'nm_field_permission', 'field'}
ADMIN_PERMISSION_READ_ENTITIES = ADMIN_PERMISSION_ENTITIES | {'user', 'department', 'subdepartment', 'level'}


# Cuanto se recuerda que un usuario sigue vigente. Es el retraso maximo con que un
# despido o un cambio de rol surte efecto sobre una sesion ya abierta (por proceso).
VIGENCIA_DE_SESION_SEGUNDOS = int(os.getenv('SESSION_REVALIDATE_SECONDS', '30'))
_vigencia: dict[int, tuple[float, bool, int | None]] = {}


def olvidar_vigencias() -> None:
    _vigencia.clear()


def sesion_vigente(user_data: dict) -> bool:
    """El token es una foto de hace hasta 8 horas: sin esto, dar de baja a alguien o
    quitarle un rol no hacia nada hasta que el token expiraba. Se revisa contra la
    base (con una cache corta) que el usuario exista, no este dado de baja y siga
    con el rol del token."""
    import time

    if str(os.getenv('TESTING') or '').strip().lower() in {'1', 'true', 'yes'}:
        return True
    try:
        id_user = int(user_data.get('id_user') or user_data.get('user_id') or 0)
    except (TypeError, ValueError):
        return False
    if not id_user:
        return False
    ahora = time.monotonic()
    guardado = _vigencia.get(id_user)
    if guardado is None or guardado[0] < ahora:
        from sqlalchemy import select
        from app.models.session import transaction_context
        from app.models.user import User

        with transaction_context() as db:
            fila = db.execute(select(User.deletion_date, User.id_permission)
                              .where(User.id_user == id_user)).first()
        guardado = (ahora + VIGENCIA_DE_SESION_SEGUNDOS,
                    fila is not None and fila[0] is None,
                    fila[1] if fila is not None else None)
        _vigencia[id_user] = guardado
    _, vivo, permiso_actual = guardado
    if not vivo:
        return False
    permiso_token = _get_permission_id(user_data)
    return permiso_token is None or permiso_actual is None or int(permiso_actual) == permiso_token


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
        # El token del paso 1 del login con MFA (solo contrasena) no es una
        # sesion: solo `/auth/mfa/verify-login` lo acepta, y lo decodifica aparte.
        if user_data.get('mfa_step'):
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

    scope_column = PERMISSION_SCOPE_COLUMNS.get(action)
    if scope_column is None:
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
            scope = int(getattr(record, scope_column))
        except (TypeError, ValueError):
            return False
        return scope != 0


def has_kpi_permission(session, user_data: dict, id_kpi_definition) -> bool:
    """Si el actor puede ver este KPI puntual.

    Dos capas, igual que `_has_entity_permission`, pero la primera mira el
    modulo DEL KPI (`kpi_definition.modulo`, ej. "facturacion"), no el modulo
    "kpis" del registro: un cliente puede tener "kpis" contratado sin tener
    "facturacion", y en ese caso sus KPIs de facturacion no existen para
    nadie, con independencia del rol. `require_entity_permission('kpi_definition',
    ...)` ya cubre el guardia de modulo "kpis"; este es el guardia del modulo
    que el KPI mide.

    No hay accion mas alla de "ver": un KPI no se crea/edita/borra desde
    aqui (eso lo administra `nm_permission_kpi` como entidad, via
    `require_entity_permission('nm_permission_kpi', ...)`), asi que
    `nm_permission_kpi.puede_ver` es un booleano, no un bitmask.

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
    return bool(record) and bool(record.puede_ver)


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
