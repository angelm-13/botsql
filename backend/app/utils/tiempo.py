"""El reloj del sistema: una sola convencion para las fechas.

Que se guarda y que se muestra
------------------------------
* Las columnas de auditoria -`creation_date`, `last_update_date`,
  `deletion_date`- las llena el sistema y se guardan en **UTC**. La base corre
  con la sesion en UTC (`models/session.py`), asi que `now()` ya lo es.
* La API las entrega con su zona explicita (`...Z`), nunca como una hora
  "pelona" que cada pantalla interpreta a su manera. Antes salian sin zona y la
  pantalla las tomaba por hora local: 8:33 p.m. donde eran las 2:33 p.m.
* Las fechas de negocio que captura una persona o un dispositivo
  (`incident_date`, un cierre, un vencimiento) son la hora de pared del cliente
  y se guardan tal cual, sin zona: ahi no hay nada que convertir.
* La pantalla convierte a la zona del negocio (`APP_TIMEZONE`, por omision
  America/Mexico_City, UTC-6 todo el año desde 2022) solo al mostrar.

Cambiar de zona es cambiar `APP_TIMEZONE`; no hay que tocar datos.
"""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import Date, DateTime, cast, func, literal_column
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.expression import FunctionElement

ZONA_POR_OMISION = "America/Mexico_City"


def _cargar_zona() -> timezone | ZoneInfo:
    nombre = os.getenv("APP_TIMEZONE", ZONA_POR_OMISION)
    try:
        return ZoneInfo(nombre)
    except ZoneInfoNotFoundError:
        # Una instalacion sin base de zonas horarias (tzdata) no debe tumbar el
        # arranque: se cae al desfase fijo que usa el negocio.
        return timezone(timedelta(hours=-6))


ZONA_NEGOCIO = _cargar_zona()

# Nombre IANA de la zona, para escribirlo en SQL. El desfase fijo de respaldo es `Etc/GMT+6`
# (en IANA el signo va invertido: GMT+6 es UTC-6).
NOMBRE_ZONA_SQL = getattr(ZONA_NEGOCIO, "key", None) or "Etc/GMT+6"


def ahora_utc() -> datetime:
    """Ahora en UTC, sin zona: como se guardan las columnas de auditoria."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def ahora_negocio() -> datetime:
    """Ahora en la hora de pared del negocio, sin zona.

    Para comparar o completar fechas que una persona captura en su hora local
    (`incident_date`, cierres); no para columnas de auditoria.
    """
    return datetime.now(ZONA_NEGOCIO).replace(tzinfo=None)


def a_iso_utc(valor):
    """Una fecha de auditoria como texto ISO con zona explicita (`...Z`).

    Una fecha sin zona se toma por UTC (asi se guardan); una con zona se
    convierte. `None` sigue siendo `None` y una `date` pura no lleva zona.
    """
    if valor is None:
        return None
    if isinstance(valor, datetime):
        if valor.tzinfo is not None:
            valor = valor.astimezone(timezone.utc).replace(tzinfo=None)
        return valor.isoformat() + "Z"
    if isinstance(valor, date):
        return valor.isoformat()
    return valor


def hoy_negocio() -> date:
    """El dia de hoy en la zona del negocio, no el del contenedor (que corre en UTC)."""
    return ahora_negocio().date()


def rango_utc_de_dias(fecha_inicio: date, fecha_fin: date) -> tuple[datetime, datetime]:
    """`[inicio, fin)` en UTC (sin zona) que cubre del primer al ultimo dia LOCAL, ambos incluidos.

    Para acotar una consulta sobre una columna en UTC por indice o por volumen antes de aplicar
    `dia_local`. Respeta el horario de verano de cada fecha si la zona lo tiene.
    """
    def a_utc(dia: date) -> datetime:
        return datetime.combine(dia, datetime.min.time(), ZONA_NEGOCIO).astimezone(timezone.utc).replace(tzinfo=None)

    return a_utc(fecha_inicio), a_utc(fecha_fin + timedelta(days=1))


class dia_local(FunctionElement):  # noqa: N801 -- se usa como una funcion SQL
    """Expresion SQL: el DIA, en la zona del negocio, de una columna guardada en UTC.

    Una venta cobrada a las 20:00 hora de Mexico se guarda como 02:00 UTC del dia siguiente;
    `date(columna)` la contaria en ese dia. Esta expresion la regresa al dia en que ocurrio.
    Solo para columnas de auditoria/eventos en UTC (`paid_at`, `sent_at`...), nunca para las
    fechas de pared que captura una persona (`incident_date`): esas ya son locales.

    * PostgreSQL: `CAST(timezone(zona, timezone('UTC', columna)) AS DATE)`, con la base de
      zonas de Postgres (respeta el horario de verano de cada fecha).
    * SQLite (solo las pruebas; no tiene zonas): `date(columna, '<desfase> hours')` con el
      desfase que la zona tiene hoy. Exacto para America/Mexico_City (UTC-6 fijo desde 2022).
    """

    type = Date()
    inherit_cache = True
    name = "dia_local"

    def __init__(self, columna):
        super().__init__(columna)


@compiles(dia_local)
def _dia_local_generico(element, compiler, **kw):
    columna = list(element.clauses)[0]
    return compiler.process(func.date(columna), **kw)


@compiles(dia_local, "postgresql")
def _dia_local_postgres(element, compiler, **kw):
    columna = list(element.clauses)[0]
    en_utc = func.timezone(literal_column("'UTC'"), columna)
    local = func.timezone(literal_column(f"'{NOMBRE_ZONA_SQL}'"), en_utc)
    return compiler.process(cast(local, Date), **kw)


@compiles(dia_local, "sqlite")
def _dia_local_sqlite(element, compiler, **kw):
    columna = list(element.clauses)[0]
    minutos = int(datetime.now(ZONA_NEGOCIO).utcoffset().total_seconds() // 60)
    return compiler.process(func.date(columna, literal_column(f"'{minutos:+d} minutes'")), **kw)


class menor_de(FunctionElement):  # noqa: N801
    """El menor de dos valores NO nulos (`least` en PostgreSQL, `min(a, b)` en SQLite)."""

    type = DateTime()
    inherit_cache = True
    name = "menor_de"


class mayor_de(FunctionElement):  # noqa: N801
    """El mayor de dos valores NO nulos (`greatest` en PostgreSQL, `max(a, b)` en SQLite)."""

    type = DateTime()
    inherit_cache = True
    name = "mayor_de"


@compiles(menor_de)
def _menor_de_generico(element, compiler, **kw):
    return compiler.process(func.min(*element.clauses), **kw)  # SQLite: min con varios argumentos


@compiles(menor_de, "postgresql")
def _menor_de_postgres(element, compiler, **kw):
    return compiler.process(func.least(*element.clauses), **kw)


@compiles(mayor_de)
def _mayor_de_generico(element, compiler, **kw):
    return compiler.process(func.max(*element.clauses), **kw)


@compiles(mayor_de, "postgresql")
def _mayor_de_postgres(element, compiler, **kw):
    return compiler.process(func.greatest(*element.clauses), **kw)
