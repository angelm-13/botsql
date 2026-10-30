"""Alcance por accion de entity_permission: que significa cada valor.

Cada accion (crear/leer/actualizar/eliminar) guarda un entero que se lee como
MASCARA DE BITS, no como enum cerrado:

    0 Sin acceso | 1 Propios | 2 Mis grupos | 4 Todos

Hoy el Gestor ofrece un solo valor por casilla, pero 3, 5, 6 y 7 son validos en
la base (la validacion admite 0..7) y significan la UNION: 3 = Propios + Mis
grupos; cualquier valor con el bit 4 ve todo.

  * Propios     -> el registro cuyo dueno es el actor.
  * Mis grupos  -> el dueno es un miembro de algun equipo (`team`/`nm_team_user`)
                   del que el actor tambien es miembro. Quien no esta en ningun
                   equipo solo se tiene a si mismo: equivale a Propios.
  * Todos       -> sin filtro.

Quien es el "dueno" lo define cada modulo (en vales: responsable, capturista o
quien recoge la herramienta); este archivo solo resuelve QUE personas cubre el
alcance del actor.

Las capacidades (autorizar un vale, recibir una compra...) no son registros con
dueno: solo admiten Sin acceso o Todos (`capacidad_solo_todos`), salvo las que
filtran de verdad por dueno (`ENTIDADES_CON_ALCANCE_DE_DUENO`, p. ej. el prevale).
"""

from __future__ import annotations

SCOPE_NONE = 0
SCOPE_OWN = 1
SCOPE_GROUPS = 2
SCOPE_ALL = 4

ACTION_COLUMNS = {
    "create": "scope_create",
    "read": "scope_read",
    "update": "scope_update",
    "delete": "scope_delete",
}


def _sin_restriccion(user_data: dict | None) -> bool:
    # Solo el superusuario esta por encima del Gestor. `user_type` es la
    # naturaleza de la cuenta (admin/client/employee...), no un permiso: quien
    # administra una instalacion lo hace con el rol que se le asigno.
    datos = user_data or {}
    return bool(datos.get("is_superuser") or datos.get("is_bootstrap_admin"))


def scope_bits(db, user_data: dict | None, entity_name: str, action: str) -> int:
    """El alcance (mascara de bits) del rol del actor en `entity_name`/`action`."""
    if _sin_restriccion(user_data):
        return SCOPE_ALL
    columna = ACTION_COLUMNS.get(action)
    if columna is None:
        return SCOPE_NONE
    datos = user_data or {}
    try:
        permission_id = int(datos.get("id_permission") or datos.get("permission_id") or 0)
    except (TypeError, ValueError):
        return SCOPE_NONE
    if not permission_id:
        return SCOPE_NONE

    from app.models.entity_permission import EntityPermission

    registro = (
        db.query(EntityPermission)
        .filter(EntityPermission.id_permission == permission_id)
        .filter(EntityPermission.entity_name == entity_name)
        .filter(EntityPermission.deletion_date.is_(None))
        .first()
    )
    if registro is None:
        return SCOPE_NONE
    try:
        return int(getattr(registro, columna) or 0)
    except (TypeError, ValueError):
        return SCOPE_NONE


def team_member_ids(db, actor_id: int) -> set[int]:
    """El actor y todos los miembros de los equipos de los que forma parte.

    Union de todos sus equipos. Los equipos y las membresias dados de baja no
    cuentan. Una sola consulta (auto-union de `nm_team_user`).
    """
    from sqlalchemy import select

    from app.models.nm_team_user import NmTeamUser
    from app.models.team import Team

    mis_equipos = (
        select(NmTeamUser.id_team)
        .join(Team, Team.id_team == NmTeamUser.id_team)
        .where(
            NmTeamUser.id_user == int(actor_id),
            NmTeamUser.deletion_date.is_(None),
            Team.deletion_date.is_(None),
        )
    )
    companeros = db.scalars(
        select(NmTeamUser.id_user).where(
            NmTeamUser.id_team.in_(mis_equipos),
            NmTeamUser.deletion_date.is_(None),
        )
    ).all()
    return {int(actor_id), *(int(i) for i in companeros)}


def owner_ids(db, user_data: dict | None, bits: int) -> set[int] | None:
    """Las personas cuyo registro puede tocar el actor con este alcance.

    `None` significa "todas" (bit 4): no hay filtro. Un conjunto vacio significa
    que el alcance no cubre a nadie (Sin acceso).
    """
    if bits & SCOPE_ALL:
        return None
    try:
        actor = int((user_data or {}).get("id_user") or 0)
    except (TypeError, ValueError):
        actor = 0
    duenos: set[int] = set()
    if not actor:
        return duenos
    if bits & SCOPE_OWN:
        duenos.add(actor)
    if bits & SCOPE_GROUPS:
        duenos |= team_member_ids(db, actor)
    return duenos


# Modulos donde Propios / Mis grupos FILTRAN de verdad hoy. En los demas, 1 y 2
# se comportan como Todos (el guardia es booleano), asi que el Gestor solo
# ofrece Sin acceso / Todos: para sumar uno hay que declarar su columna de dueno
# en el servicio y agregarlo aqui.
#   warehouse_prevoucher -> vales de almacen (ver `_del_solicitante`)
#   kpi_definition       -> cifras por persona (ver `routes/kpi.py`)
#   proyect, incident, daily_activity_log -> ya tenian su regla de dueno (por
#       capacidad); aqui la celda solo AMPLIA con el equipo: Mis grupos suma lo de
#       los companeros; Propios y Todos dejan la regla como estaba (un Supervisor
#       sembrado en Todos no pasa a ver todos los proyectos).
ENTIDADES_CON_ALCANCE_DE_DUENO = frozenset({
    "warehouse_prevoucher", "kpi_definition",
    "proyect", "incident", "daily_activity_log",
})


def soporta_alcance_de_dueno(entity_name: str) -> bool:
    return entity_name in ENTIDADES_CON_ALCANCE_DE_DUENO


def companeros(db, user_data: dict | None, entity_name: str) -> set[int]:
    """Las personas cuyo trabajo ve el actor ADEMAS del suyo en este modulo.

    Con Mis grupos (bit 2) en la lectura del modulo: los miembros de los equipos
    del actor, el actor incluido. Sin Mis grupos: solo el actor. Es lo que usan
    los modulos que ya tienen su propia regla de dueno (proyectos, incidencias,
    bitacora) para sumar al equipo sin cambiar lo que ya hacian.
    """
    try:
        actor = int((user_data or {}).get("id_user") or (user_data or {}).get("user_id") or 0)
    except (TypeError, ValueError):
        actor = 0
    if not actor:
        return set()
    if scope_bits(db, user_data, entity_name, "read") & SCOPE_GROUPS:
        return team_member_ids(db, actor)
    return {actor}


def capacidad_solo_todos(entity_name: str) -> bool:
    """Las capacidades no tienen dueno: Propios/Mis grupos no significan nada."""
    from app.modules.registry import CAPACIDAD_POR_CLAVE

    return entity_name in CAPACIDAD_POR_CLAVE and not soporta_alcance_de_dueno(entity_name)
