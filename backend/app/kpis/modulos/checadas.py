"""KPIs de checadas de asistencia (entrada y salida).

Una checada NO tiene tabla propia: es una fila de `incident`. El flujo de n8n por WhatsApp la crea
al marcar la entrada (`incident_date`, `latitude`, `longitude`, `distance_m`) y la cierra al marcar
la salida (`close_date`). Todos los KPIs son del modulo `operaciones` y, como los de incidencias de
siempre, sin alcance por proyecto: `incident.id_proyect` no interviene.

El criterio de checada vive en UN lugar, `es_checada()`; las consultas de este archivo (y las que
vengan, como "marcas fuera de radio") lo reutilizan en vez de repetirlo.

Equipo = parque. La relacion es `incident.id_user` -> `nm_team_user` -> `team`. Una persona puede
estar en varios equipos y cuenta en CADA uno. Una persona SIN equipo vigente (sin membresia, o solo
en equipos dados de baja) sale en una fila propia, "Sin equipo" (`sin_asignar=True`), y NO cuenta en
ningun equipo; quien tiene equipo nunca cuenta en "Sin equipo". Por eso estos KPIs NO se pueden
sumar entre equipos: ver `graficas_permitidas` mas abajo.

Tiempo. `incident_date` y `close_date` son hora de pared del negocio (GMT-6) SIN zona; `creation_date`
es UTC y aqui no se usa. "Ahora", "hoy" y la antiguedad salen de `app.utils.tiempo.ahora_negocio()`,
nunca de `now()` en UTC: el dia UTC cambia a las 18:00 de Mexico y ahi se equivocaria el "hoy".
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import Date, exists, func, or_, select, type_coerce

from app.models.incident import Incident
from app.models.nm_team_user import NmTeamUser
from app.models.team import Team
from app.utils.tiempo import ahora_negocio

# Una checada abierta cuenta como "en turno" mientras lleve MENOS de este tiempo abierta; con esto o mas
# es "sin salida" (se olvido de marcar). Una entrada exactamente a 12 horas ya es "sin salida".
UMBRAL_SIN_SALIDA_HORAS = 12
UMBRAL_SIN_SALIDA = timedelta(hours=UMBRAL_SIN_SALIDA_HORAS)

# Una checada CERRADA que dura MAS de este tiempo entre la entrada y la salida casi seguro tiene la salida mal capturada
# (se olvido de marcarla y se cerro despues): no es tiempo trabajado. Exactamente 16 horas SI cuenta. Las que pasan el tope
# no suman en `horas_trabajadas_por_empleado` y se reportan aparte en `checadas_con_duracion_anomala`.
TOPE_DURACION_CHECADA_HORAS = 16
TOPE_DURACION_CHECADA = timedelta(hours=TOPE_DURACION_CHECADA_HORAS)

# Estatus con el que se anula una incidencia (`INCIDENT_CLOSED_STATUSES` en operations_workflow). Una checada
# cancelada es un error de captura: no es una entrada, ni una salida, ni horas trabajadas.
ESTATUS_CANCELADA = "cancelada"

CENTESIMAS = Decimal("0.01")


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


def _tiene_equipo():
    """Condicion SQL: la persona de la checada esta en al menos un equipo VIGENTE (membresia y equipo sin baja).

    Es un `NOT EXISTS` y no un `LEFT JOIN` a proposito: con el `LEFT JOIN`, quien tiene un equipo vigente y otro
    dado de baja saldria tambien como "sin equipo".
    """
    return exists(
        select(NmTeamUser.id_nm_team_user)
        .join(Team, Team.id_team == NmTeamUser.id_team)
        .where(
            NmTeamUser.id_user == Incident.id_user,
            NmTeamUser.deletion_date.is_(None),
            Team.deletion_date.is_(None),
        )
    )


def _personas_sin_equipo(session, *condiciones) -> int:
    """Personas DISTINTAS con una checada que cumple `condiciones` y ningun equipo vigente."""
    return int(session.scalar(
        select(func.count(func.distinct(Incident.id_user)))
        .where(*checadas_vigentes(), ~_tiene_equipo(), *condiciones)
    ) or 0)


def _foto_por_equipo(session, fecha_fin, antiguedad):
    """Una fila por equipo vigente, fechada en `fecha_fin`, SOLO si `fecha_fin` es hoy (dia local).

    * Es una foto de AHORA: "quien esta en turno ahora" no se puede reconstruir para otro dia. Si `fecha_fin` no es
      el dia local de hoy (un backfill de un rango pasado, o un contenedor en UTC que ya cambio de dia a las
      18:00 de Mexico) no se emite nada, en lugar de guardar el estado de ahora bajo una fecha que no es.
    * Cada equipo vigente sale CON SU CERO. Es obligatorio: el upsert solo actualiza las filas que la consulta
      regresa, asi que un equipo que pasa de 3 personas a 0 y no saliera conservaria el 3 para siempre. Lo mismo
      vale para "Sin equipo" (entidad `None`): sale siempre, con su cero.
    * No filtra por dia calendario: una entrada de las 23:50 sigue "en turno" a las 00:10 del dia siguiente.
    """
    ahora = ahora_negocio()
    if fecha_fin != ahora.date():
        return []
    condiciones = (Incident.close_date.is_(None), antiguedad(Incident.incident_date, ahora - UMBRAL_SIN_SALIDA))
    conteos = _personas_por_equipo(session, *condiciones)
    filas = [(id_team, fecha_fin, conteos.get(id_team, 0)) for id_team in _equipos_vigentes(session)]
    return filas + [(None, fecha_fin, _personas_sin_equipo(session, *condiciones))]


def checadas_en_turno_por_equipo_query(session, fecha_inicio, fecha_fin, filtros_dimension, actor_project):
    """Foto: personas distintas con una checada ABIERTA (sin `close_date`) de MENOS de 12 horas, por equipo.

    "Abierta" es no tener `close_date`: una checada en `abierta` o en `en_proceso` cuenta. Mas la fila "Sin equipo".
    """
    return _foto_por_equipo(session, fecha_fin, lambda columna, corte: columna > corte)


def checadas_sin_salida_por_equipo_query(session, fecha_inicio, fecha_fin, filtros_dimension, actor_project):
    """Foto: personas distintas con una checada ABIERTA de 12 horas o MAS (olvidaron marcar la salida), por equipo."""
    return _foto_por_equipo(session, fecha_fin, lambda columna, corte: columna <= corte)


# --- foto por persona: quien esta en turno y cuanto lleva ----------------------------------------

def checadas_en_turno_por_empleado_query(session, fecha_inicio, fecha_fin, filtros_dimension, actor_project):
    """Foto: minutos que lleva en turno cada persona con una checada ABIERTA de MENOS de 12 horas.

    * Valor: minutos desde la ENTRADA. Si una persona tiene varias abiertas de menos de 12 horas, cuenta la MAS RECIENTE
      (la que esta en curso; una mas vieja es casi seguro una entrada duplicada).
    * Quien ya no esta en turno sale en CERO, no desaparece: el upsert solo actualiza lo que la consulta devuelve, asi que
      sin ese cero el valor de hace un rato se quedaria pegado. Los candidatos son todas las personas con una checada que
      EMPEZO desde 12 horas antes de que comenzara hoy: nadie que entrara antes pudo estar en turno hoy. Se calculan sin
      mirar si la checada se cancelo o se borro: una checada anulada despues de contar tambien debe dejar de contar.
      La API omite esos ceros (`ocultar_ceros`): el Dashboard solo pinta a quien esta en turno.
    * Una foto de AHORA: solo se emite si `fecha_fin` es el dia local de hoy (ver `_foto_por_equipo`).
    """
    ahora = ahora_negocio()
    if fecha_fin != ahora.date():
        return []
    en_curso = dict(session.execute(
        select(Incident.id_user, func.max(Incident.incident_date))
        .where(*checadas_vigentes(), Incident.close_date.is_(None), Incident.incident_date > ahora - UMBRAL_SIN_SALIDA)
        .group_by(Incident.id_user)
    ).all())
    desde = datetime.combine(ahora.date(), time.min) - UMBRAL_SIN_SALIDA
    candidatos = set(session.scalars(
        select(func.distinct(Incident.id_user)).where(es_checada(), Incident.incident_date >= desde)
    ))
    filas = []
    for id_user in sorted(candidatos | set(en_curso)):
        entrada = en_curso.get(id_user)
        minutos = max(Decimal(0), Decimal((ahora - entrada).total_seconds()) / 60) if entrada else Decimal(0)
        filas.append((int(id_user), fecha_fin, minutos.quantize(CENTESIMAS)))
    return filas


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


def _marcas_sin_equipo_por_dia(session, fecha_col, fecha_inicio, fecha_fin, *condiciones):
    filas = session.execute(
        select(fecha_col.label("fecha"), func.count(func.distinct(Incident.id_incident)))
        .where(
            *checadas_vigentes(),
            ~_tiene_equipo(),
            fecha_col >= fecha_inicio,
            fecha_col <= fecha_fin,
            *condiciones,
        )
        .group_by(fecha_col)
    ).all()
    return {fecha: int(marcas) for fecha, marcas in filas}


def _flujo_por_equipo(session, fecha_col, fecha_inicio, fecha_fin, *condiciones):
    """Una fila por equipo vigente y por dia del rango, mas una de "Sin equipo" (entidad `None`) por dia.

    Cada equipo sale CON SU CERO cada dia, no solo los dias con marcas. Igual que en las fotos: el upsert solo actualiza lo
    que la consulta devuelve, asi que si se cancela la unica entrada de un dia y la fila en cero no saliera, el valor viejo se
    quedaria pegado. Con la corrida de 5 minutos (que recalcula solo hoy) esto pasa en el mismo dia.
    Orden: los equipos por id, cada uno con sus dias; al final "Sin equipo".
    """
    por_equipo = {(id_team, dia): n for id_team, dia, n in _marcas_por_equipo_y_dia(session, fecha_col, fecha_inicio, fecha_fin, *condiciones)}
    sin_equipo = _marcas_sin_equipo_por_dia(session, fecha_col, fecha_inicio, fecha_fin, *condiciones)
    dias = [fecha_inicio + timedelta(days=i) for i in range((fecha_fin - fecha_inicio).days + 1)]
    filas = [
        (id_team, dia, por_equipo.get((id_team, dia), 0))
        for id_team in _equipos_vigentes(session) for dia in dias
    ]
    return filas + [(None, dia, sin_equipo.get(dia, 0)) for dia in dias]


def checadas_entradas_por_equipo_query(session, fecha_inicio, fecha_fin, filtros_dimension, actor_project):
    """Entradas (checadas abiertas ese dia) por equipo y por dia local de `incident_date`, mas "Sin equipo".

    Cuenta checadas, no personas: dos entradas de la misma persona el mismo dia son dos. Una entrada que se marca a
    las 23:50 es del dia en que se marco, aunque la salida sea a las 00:10 del siguiente. Una fila por equipo y por dia
    del rango, con su cero (ver `_flujo_por_equipo`).
    """
    return _flujo_por_equipo(session, _dia(Incident.incident_date), fecha_inicio, fecha_fin)


def checadas_salidas_por_equipo_query(session, fecha_inicio, fecha_fin, filtros_dimension, actor_project):
    """Salidas (checadas cerradas ese dia) por equipo y por dia local de `close_date`, mas "Sin equipo".

    Una salida a las 00:10 es del dia siguiente al de su entrada de las 23:50. Una fila por equipo y por dia del rango,
    con su cero (ver `_flujo_por_equipo`).
    """
    return _flujo_por_equipo(
        session, _dia(Incident.close_date), fecha_inicio, fecha_fin, Incident.close_date.isnot(None),
    )


# --- horas trabajadas ------------------------------------------------------------------------

def _supera_el_tope(abre, cierra) -> bool:
    """La checada cerrada dura MAS de `TOPE_DURACION_CHECADA` (16 h exactas no lo supera). Es el unico lugar que lo decide."""
    return cierra - abre > TOPE_DURACION_CHECADA


def horas_trabajadas_por_empleado_query(session, fecha_inicio, fecha_fin, filtros_dimension, actor_project):
    """Minutos trabajados por empleado y por dia: `close_date - incident_date` de las checadas CERRADAS.

    * Dia: el de la ENTRADA (`incident_date`). Un turno nocturno de 23:50 a 00:10 son 20 minutos del dia en que
      empezo, no se parten en dos dias.
    * Una checada abierta no suma (todavia no se sabe cuanto va a durar) y una cancelada tampoco.
    * Una cerrada con MAS de `TOPE_DURACION_CHECADA_HORAS` (16) entre la entrada y la salida tampoco suma: casi seguro la
      salida se olvido y se capturo despues. Se cuenta aparte en `checadas_con_duracion_anomala`, que la fecha por el dia
      de la SALIDA (este KPI usa el de la entrada). Con exactamente 16 horas SI suma.
    * No depende del equipo: quien no tiene equipo tambien suma.
    * Se suma en Python y no en SQL: restar fechas es distinto en SQLite y en PostgreSQL, y el rango es de siete dias
      en la corrida nocturna, asi que son pocas filas.
    """
    dia = _dia(Incident.incident_date)
    filas = session.execute(
        select(Incident.id_user, Incident.incident_date, Incident.close_date)
        .where(
            *checadas_vigentes(),
            Incident.incident_date.isnot(None),
            Incident.close_date.isnot(None),
            # Una salida anterior a su entrada no es un turno: el servicio la rechaza, pero un dato directo en BD no.
            Incident.close_date >= Incident.incident_date,
            dia >= fecha_inicio,
            dia <= fecha_fin,
        )
    ).all()
    minutos: dict[tuple[int, object], Decimal] = defaultdict(Decimal)
    for id_user, abre, cierra in filas:
        if _supera_el_tope(abre, cierra):
            continue
        minutos[(int(id_user), abre.date())] += Decimal((cierra - abre).total_seconds()) / 60
    return [
        (id_user, fecha, total.quantize(CENTESIMAS))
        for (id_user, fecha), total in sorted(minutos.items())
    ]


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
            sin_asignar=True,
            direccion="neutral",
            graficas_permitidas=barras,
            grafica_default="barras",
            descripcion=(
                f"Foto de ahora: personas distintas con una checada abierta de menos de {UMBRAL_SIN_SALIDA_HORAS} horas, "
                "por equipo, y «Sin equipo» para quien no está en ninguno. Una persona en dos equipos cuenta en cada uno: "
                "no sumes los equipos."
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
            sin_asignar=True,
            direccion="bajo_es_mejor",
            graficas_permitidas=barras,
            grafica_default="barras",
            descripcion=(
                f"Foto de ahora: personas distintas con una checada abierta de {UMBRAL_SIN_SALIDA_HORAS} horas o más "
                "(se les olvidó marcar la salida), por equipo, y «Sin equipo» para quien no está en ninguno. Una persona en "
                "dos equipos cuenta en cada uno."
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
            sin_asignar=True,
            direccion="neutral",
            graficas_permitidas=barras,
            grafica_default="barras",
            descripcion=(
                "Entradas (checadas abiertas) por equipo y por día local de la entrada, y «Sin equipo» para quien no está "
                "en ninguno. Cuenta checadas, no personas. Una persona en dos equipos cuenta en cada uno."
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
            sin_asignar=True,
            direccion="neutral",
            graficas_permitidas=barras,
            grafica_default="barras",
            descripcion=(
                "Salidas (checadas cerradas) por equipo y por día local de la salida: una salida a las 00:10 es del "
                "día siguiente a su entrada de las 23:50. «Sin equipo» para quien no está en ninguno. Una persona en dos "
                "equipos cuenta en cada uno."
            ),
        ),
        KpiDefinition(
            clave="horas_trabajadas_por_empleado",
            etiqueta="Tiempo trabajado por empleado",
            modulo="operaciones",
            dimensiones=("empleado",),
            query_builder=horas_trabajadas_por_empleado_query,
            agregacion="suma",
            unidad="minutos",
            alcance_proyecto=False,
            direccion="neutral",
            graficas_permitidas=barras,
            grafica_default="barras",
            descripcion=(
                "Minutos trabajados por empleado: suma de (salida - entrada) de las checadas cerradas, por día de la "
                f"entrada. Una checada sin salida todavía no suma, y una de más de {TOPE_DURACION_CHECADA_HORAS} horas "
                "tampoco (casi seguro se olvidó la salida): esas salen en «Checadas con duración anómala»."
            ),
        ),
        KpiDefinition(
            clave="checadas_en_turno_por_empleado",
            etiqueta="Tiempo en turno por empleado",
            modulo="operaciones",
            dimensiones=("empleado",),
            query_builder=checadas_en_turno_por_empleado_query,
            agregacion="ultimo",
            unidad="minutos",
            alcance_proyecto=False,
            direccion="neutral",
            graficas_permitidas=barras,
            grafica_default="barras",
            ocultar_ceros=True,
            descripcion=(
                f"Foto de ahora: quién está en turno y cuántos minutos lleva desde su entrada (checada abierta de menos de "
                f"{UMBRAL_SIN_SALIDA_HORAS} horas). Si tiene varias abiertas, cuenta la más reciente. Quien ya no está en "
                "turno no aparece."
            ),
        ),
    )
