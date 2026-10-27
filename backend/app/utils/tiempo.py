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


def a_hora_negocio(valor: datetime) -> datetime:
    """Una fecha que trae un dispositivo, como hora de pared del negocio sin zona.

    Con zona (`-06:00`, `Z`) se convierte a la del negocio; sin zona se toma
    como ya local y se deja igual.
    """
    if valor.tzinfo is not None:
        valor = valor.astimezone(ZONA_NEGOCIO)
    return valor.replace(tzinfo=None)


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


def pared_a_utc(instante: datetime) -> datetime:
    """Una hora de pared del negocio (sin zona) como instante UTC (sin zona).

    Es la conversion que hace falta antes de comparar una fecha de negocio (`incident_date`, `close_date`:
    hora de pared GMT-6) con una columna de auditoria (`creation_date`, `deletion_date`: UTC). Sin ella, una
    marca de las 20:00 en Mexico se compara como si fueran las 20:00 UTC, seis horas antes de lo que paso.
    """
    if instante.tzinfo is not None:
        return instante.astimezone(timezone.utc).replace(tzinfo=None)
    return instante.replace(tzinfo=ZONA_NEGOCIO).astimezone(timezone.utc).replace(tzinfo=None)


def utc_a_pared(instante: datetime) -> datetime:
    """Lo inverso de `pared_a_utc`: un instante UTC (sin zona) como hora de pared del negocio (sin zona)."""
    if instante.tzinfo is None:
        instante = instante.replace(tzinfo=timezone.utc)
    return instante.astimezone(ZONA_NEGOCIO).replace(tzinfo=None)


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


class hora_pared_a_utc(FunctionElement):  # noqa: N801 -- se usa como una funcion SQL
    """Expresion SQL: una hora de pared del negocio (sin zona) como instante UTC (sin zona).

    Lo inverso de `dia_local` y el equivalente en SQL de `pared_a_utc`: para comparar `incident_date` o
    `close_date` (hora de pared) con `creation_date` o `deletion_date` (UTC) dentro de una consulta.

    * PostgreSQL: `timezone('UTC', timezone(zona, columna))`: la primera interpreta la hora de pared en la zona del
      negocio (con su horario de verano, si lo hubiera) y la segunda la regresa a UTC.
    * SQLite (solo las pruebas): suma el desfase que la zona tiene hoy y conserva la parte fraccionaria del
      original, para que la comparacion sea exacta al microsegundo. Exacto para America/Mexico_City (UTC-6 fijo
      desde 2022).
    """

    type = DateTime()
    inherit_cache = True
    name = "hora_pared_a_utc"

    def __init__(self, columna):
        super().__init__(columna)


@compiles(hora_pared_a_utc)
def _hora_pared_a_utc_generico(element, compiler, **kw):
    columna = list(element.clauses)[0]
    return compiler.process(columna, **kw)


@compiles(hora_pared_a_utc, "postgresql")
def _hora_pared_a_utc_postgres(element, compiler, **kw):
    columna = list(element.clauses)[0]
    en_la_zona = func.timezone(literal_column(f"'{NOMBRE_ZONA_SQL}'"), columna)
    return compiler.process(func.timezone(literal_column("'UTC'"), en_la_zona), **kw)


@compiles(hora_pared_a_utc, "sqlite")
def _hora_pared_a_utc_sqlite(element, compiler, **kw):
    columna = list(element.clauses)[0]
    minutos = -int(datetime.now(ZONA_NEGOCIO).utcoffset().total_seconds() // 60)
    entero = func.strftime("%Y-%m-%d %H:%M:%S", columna, literal_column(f"'{minutos:+d} minutes'"))
    return compiler.process(entero.op("||")(func.substr(columna, 20)), **kw)


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
