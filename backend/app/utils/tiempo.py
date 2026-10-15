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
