"""KPIs de checadas de asistencia (entrada y salida).

Una checada NO tiene tabla propia: es una fila de `incident`. El flujo de n8n por WhatsApp la crea
al marcar la entrada (`incident_date`, `latitude`, `longitude`, `distance_m`) y la cierra al marcar
la salida (`close_date`). Todos los KPIs son del modulo `operaciones` y, como los de incidencias de
siempre, sin alcance por proyecto: `incident.id_proyect` no interviene.

El criterio de checada vive en UN lugar, `es_checada()`; las consultas de este archivo (y las que
vengan, como "marcas fuera de radio") lo reutilizan en vez de repetirlo.

Equipo = parque. La relacion es `incident.id_user` -> `nm_team_user` -> `team`. Una persona puede
estar en varios equipos y cuenta en CADA uno; una persona sin equipo no aparece en los KPIs por
equipo (no hay a quien atribuirla) pero si en el de horas por empleado. Por eso estos KPIs NO se
pueden sumar entre equipos: ver `graficas_permitidas` mas abajo.

Tiempo. `incident_date` y `close_date` son hora de pared del negocio (GMT-6) SIN zona; `creation_date`
es UTC y aqui no se usa. "Ahora", "hoy" y la antiguedad salen de `app.utils.tiempo.ahora_negocio()`,
nunca de `now()` en UTC: el dia UTC cambia a las 18:00 de Mexico y ahi se equivocaria el "hoy".
"""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import Date, func, or_, select, type_coerce

from app.models.incident import Incident
from app.models.nm_team_user import NmTeamUser
from app.models.team import Team
from app.utils.tiempo import ahora_negocio

# Una checada abierta cuenta como "en turno" mientras lleve MENOS de este tiempo abierta; con esto o mas
# es "sin salida" (se olvido de marcar). Una entrada exactamente a 12 horas ya es "sin salida".
UMBRAL_SIN_SALIDA_HORAS = 12
UMBRAL_SIN_SALIDA = timedelta(hours=UMBRAL_SIN_SALIDA_HORAS)

# Estatus con el que se anula una incidencia (`INCIDENT_CLOSED_STATUSES` en operations_workflow). Una checada
# cancelada es un error de captura: no es una entrada, ni una salida, ni horas trabajadas.
ESTATUS_CANCELADA = "cancelada"


# --- el criterio de checada ----------------------------------------------------------------

def es_checada():
    """Condicion SQL: la fila de `incident` es una checada.

    Una checada trae latitud; el resto de las incidencias (y los vales de almacen, que tambien son `incident`)
    no. Es el criterio que la pantalla de incidencias ya usa para mostrar las columnas de coordenadas
    (`IncidentPage.jsx`, `tieneDatosDeChecada`).
    """
    return Incident.latitude.isnot(None)


def checadas_vigentes():
    """Condiciones comunes de todas las consultas: es checada, sin baja y no cancelada."""
    return [
        Incident.deletion_date.is_(None),
        es_checada(),
        or_(Incident.incident_status.is_(None), Incident.incident_status != ESTATUS_CANCELADA),
    ]


def _dia(columna):
    # `date(columna)` sobre una hora de pared ya es el dia local: no hay nada que convertir. `type_coerce` hace
    # que SQLite (solo pruebas) regrese un `date` y no el texto, igual que PostgreSQL.
    return type_coerce(func.date(columna), Date)


# --- fotos: personas en turno y sin salida --------------------------------------------------

def _equipos_vigentes(session) -> list[int]:
    return list(session.scalars(select(Team.id_team).where(Team.deletion_date.is_(None)).order_by(Team.id_team)))


def _personas_por_equipo(session, *condiciones) -> dict[int, int]:
    """`{id_team: personas DISTINTAS}` con una checada que cumple `condiciones`.

    Una persona con dos checadas abiertas cuenta una vez; una persona en dos equipos cuenta en los dos.
    """
    filas = session.execute(
        select(NmTeamUser.id_team, func.count(func.distinct(Incident.id_user)))
        .select_from(Incident)
        .join(NmTeamUser, NmTeamUser.id_user == Incident.id_user)
        .join(Team, Team.id_team == NmTeamUser.id_team)
        .where(
            *checadas_vigentes(),
            NmTeamUser.deletion_date.is_(None),
            Team.deletion_date.is_(None),
            *condiciones,
        )
        .group_by(NmTeamUser.id_team)
    ).all()
    return {int(id_team): int(personas) for id_team, personas in filas}


def _foto_por_equipo(session, fecha_fin, antiguedad):
    """Una fila por equipo vigente, fechada en `fecha_fin`, SOLO si `fecha_fin` es hoy (dia local).

    * Es una foto de AHORA: "quien esta en turno ahora" no se puede reconstruir para otro dia. Si `fecha_fin` no es
      el dia local de hoy (un backfill de un rango pasado, o un contenedor en UTC que ya cambio de dia a las
      18:00 de Mexico) no se emite nada, en lugar de guardar el estado de ahora bajo una fecha que no es.
    * Cada equipo vigente sale CON SU CERO. Es obligatorio: el upsert solo actualiza las filas que la consulta
      regresa, asi que un equipo que pasa de 3 personas a 0 y no saliera conservaria el 3 para siempre.
    * No filtra por dia calendario: una entrada de las 23:50 sigue "en turno" a las 00:10 del dia siguiente.
    """
    ahora = ahora_negocio()
    if fecha_fin != ahora.date():
        return []
    conteos = _personas_por_equipo(
        session,
        Incident.close_date.is_(None),
        antiguedad(Incident.incident_date, ahora - UMBRAL_SIN_SALIDA),
    )
    return [(id_team, fecha_fin, conteos.get(id_team, 0)) for id_team in _equipos_vigentes(session)]


def checadas_en_turno_por_equipo_query(session, fecha_inicio, fecha_fin, filtros_dimension, actor_project):
    """Foto: personas distintas con una checada ABIERTA (sin `close_date`) de MENOS de 12 horas, por equipo."""
    return _foto_por_equipo(session, fecha_fin, lambda columna, corte: columna > corte)


def checadas_sin_salida_por_equipo_query(session, fecha_inicio, fecha_fin, filtros_dimension, actor_project):
    """Foto: personas distintas con una checada ABIERTA de 12 horas o MAS (olvidaron marcar la salida), por equipo."""
    return _foto_por_equipo(session, fecha_fin, lambda columna, corte: columna <= corte)


# --- flujos: entradas y salidas por dia local ------------------------------------------------

def _marcas_por_equipo_y_dia(session, fecha_col, fecha_inicio, fecha_fin, *condiciones):
    filas = session.execute(
        select(NmTeamUser.id_team, fecha_col.label("fecha"), func.count(func.distinct(Incident.id_incident)))
        .select_from(Incident)
        .join(NmTeamUser, NmTeamUser.id_user == Incident.id_user)
        .join(Team, Team.id_team == NmTeamUser.id_team)
        .where(
            *checadas_vigentes(),
            NmTeamUser.deletion_date.is_(None),
            Team.deletion_date.is_(None),
            fecha_col >= fecha_inicio,
            fecha_col <= fecha_fin,
            *condiciones,
        )
        .group_by(NmTeamUser.id_team, fecha_col)
        .order_by(NmTeamUser.id_team, fecha_col)
    ).all()
    return [(int(id_team), fecha, int(marcas)) for id_team, fecha, marcas in filas]


def checadas_entradas_por_equipo_query(session, fecha_inicio, fecha_fin, filtros_dimension, actor_project):
    """Entradas (checadas abiertas ese dia) por equipo y por dia local de `incident_date`.

    Cuenta checadas, no personas: dos entradas de la misma persona el mismo dia son dos. Una entrada que se marca a
    las 23:50 es del dia en que se marco, aunque la salida sea a las 00:10 del siguiente. Solo salen los dias con datos.
    """
    return _marcas_por_equipo_y_dia(session, _dia(Incident.incident_date), fecha_inicio, fecha_fin)


def checadas_salidas_por_equipo_query(session, fecha_inicio, fecha_fin, filtros_dimension, actor_project):
    """Salidas (checadas cerradas ese dia) por equipo y por dia local de `close_date`.

    Una salida a las 00:10 es del dia siguiente al de su entrada de las 23:50. Solo salen los dias con datos.
    """
    return _marcas_por_equipo_y_dia(
        session, _dia(Incident.close_date), fecha_inicio, fecha_fin, Incident.close_date.isnot(None),
    )


# --- definiciones ----------------------------------------------------------------------------

def definiciones():
    from app.kpis.registry import KpiDefinition

    # Estos KPIs se muestran SOLO como barras. Una persona en dos equipos cuenta en cada uno, asi que el `total` que la
    # API suma entre equipos la contaria dos veces; la barra muestra un valor por equipo y no usa ese total (el
    # "numero" y la serie por periodo si lo harian). El registro no tiene una marca de "no aditivo": si algun dia se
    # permiten otras graficas, hay que agregarla.
    barras = ("barras",)

    return (
        KpiDefinition(
            clave="checadas_en_turno_por_equipo",
            etiqueta="Personas en turno por equipo",
            modulo="operaciones",
            dimensiones=("equipo",),
            etiqueta_dimension="Equipo (parque)",
            query_builder=checadas_en_turno_por_equipo_query,
            agregacion="ultimo",
            unidad="numero",
            alcance_proyecto=False,
            direccion="neutral",
            graficas_permitidas=barras,
            grafica_default="barras",
            descripcion=(
                f"Foto de ahora: personas distintas con una checada abierta de menos de {UMBRAL_SIN_SALIDA_HORAS} horas, "
                "por equipo. Una persona en dos equipos cuenta en cada uno: no sumes los equipos."
            ),
        ),
        KpiDefinition(
            clave="checadas_sin_salida_por_equipo",
            etiqueta="Personas sin salida por equipo",
            modulo="operaciones",
            dimensiones=("equipo",),
            etiqueta_dimension="Equipo (parque)",
            query_builder=checadas_sin_salida_por_equipo_query,
            agregacion="ultimo",
            unidad="numero",
            alcance_proyecto=False,
            direccion="bajo_es_mejor",
            graficas_permitidas=barras,
            grafica_default="barras",
            descripcion=(
                f"Foto de ahora: personas distintas con una checada abierta de {UMBRAL_SIN_SALIDA_HORAS} horas o más "
                "(se les olvidó marcar la salida), por equipo. Una persona en dos equipos cuenta en cada uno."
            ),
        ),
        KpiDefinition(
            clave="checadas_entradas_por_equipo",
            etiqueta="Entradas por equipo",
            modulo="operaciones",
            dimensiones=("equipo",),
            etiqueta_dimension="Equipo (parque)",
            query_builder=checadas_entradas_por_equipo_query,
            agregacion="suma",
            unidad="numero",
            alcance_proyecto=False,
            direccion="neutral",
            graficas_permitidas=barras,
            grafica_default="barras",
            descripcion=(
                "Entradas (checadas abiertas) por equipo y por día local de la entrada. Cuenta checadas, no personas. "
                "Una persona en dos equipos cuenta en cada uno."
            ),
        ),
        KpiDefinition(
            clave="checadas_salidas_por_equipo",
            etiqueta="Salidas por equipo",
            modulo="operaciones",
            dimensiones=("equipo",),
            etiqueta_dimension="Equipo (parque)",
            query_builder=checadas_salidas_por_equipo_query,
            agregacion="suma",
            unidad="numero",
            alcance_proyecto=False,
            direccion="neutral",
            graficas_permitidas=barras,
            grafica_default="barras",
            descripcion=(
                "Salidas (checadas cerradas) por equipo y por día local de la salida: una salida a las 00:10 es del "
                "día siguiente a su entrada de las 23:50. Una persona en dos equipos cuenta en cada uno."
            ),
        ),
    )
