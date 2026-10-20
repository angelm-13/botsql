"""Que KPIs se recalculan durante el dia, y cada cuanto.

Un KPI "snapshot" se calcula en la corrida nocturna (`tasks_kpis.recalculate_kpi_snapshots`, 01:00), asi
que una venta de hoy llegaria al Dashboard hasta el dia siguiente. Los modulos de aqui, cuyo gerente
mira el dia EN CURSO (restaurante, punto de venta), ademas se recalculan solo para HOY cada
`intervalo_minutos()` (`tasks_kpis.recalculate_kpi_snapshots_frecuentes`). Los demas modulos siguen
solo con la corrida nocturna.

Un KPI suelto tambien puede entrar a la corrida frecuente SIN arrastrar a todo su modulo
(`KPIS_FRECUENTES`): los KPIs de checadas de `operaciones` que el gerente mira en el momento (quien esta en turno,
sin salida, y las entradas y salidas de HOY) se recalculan cada pocos minutos; el resto de operaciones (incidencias, vales,
material) y las horas trabajadas siguen solo con la corrida nocturna.

Un dia que acaba de terminar se completa en la primera hora local: a partir de medianoche las filas de AYER de entradas y salidas se quedan con lo que
escribio la ultima corrida de 5 minutos de ese dia (pueden faltar las marcas de los ultimos minutos), y la corrida nocturna las completa hasta mucho despues.
Por eso, de las 00:00 a las 00:59 hora de Mexico, las cinco claves de `KPIS_FRECUENTES` se llaman con (ayer, hoy) en lugar de (hoy, hoy)
(`rango_de_las_claves_frecuentes`). Los modulos de `MODULOS_FRECUENTES` (restaurante, POS) siguen siempre con (hoy, hoy).

Sin imports pesados a proposito: `app/jobs/beat_schedule.py` lo lee al arrancar el beat.
"""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta

# Claves de MODULOS (`app/modules/registry.py`). "pos" aun no tiene KPIs: queda declarado para que sus
# primeros KPIs entren a la corrida frecuente sin tocar el job.
MODULOS_FRECUENTES = ("restaurante", "pos")

# Claves de KPI (`KPI_REGISTRY`) que entran a la corrida frecuente aunque su modulo no este en `MODULOS_FRECUENTES`.
# La corrida frecuente llama a cada KPI con (hoy, hoy): una foto de AHORA escribe hoy, y un KPI de rango (entradas y
# salidas por dia) recalcula SOLO las filas de hoy y no toca los demas dias ya guardados. Horas trabajadas y duraciones
# anomalas NO entran: dependen de salidas que se capturan despues, y las recalcula la corrida nocturna.
KPIS_FRECUENTES = (
    "checadas_en_turno_por_equipo",
    "checadas_sin_salida_por_equipo",
    "checadas_entradas_por_equipo",
    "checadas_salidas_por_equipo",
    "checadas_en_turno_por_empleado",
)

# Cuantas horas locales, desde la medianoche, la corrida de 5 minutos incluye tambien el dia anterior para `KPIS_FRECUENTES`: 1 es de las 00:00 a las 00:59
# (a la 01:00 en punto ya es solo hoy). Son 12 corridas con el intervalo por omision. Si se fija `CELERY_TIMEZONE` a la hora de Mexico y la corrida nocturna
# pasa a correr a la 01:00 local, esta pasada queda redundante pero inofensiva: recalcula lo mismo que la nocturna, solo antes.
HORAS_CON_AYER_TRAS_MEDIANOCHE = 1

INTERVALO_MINUTOS_POR_OMISION = 5
INTERVALO_ENV = "KPI_FRECUENTES_INTERVALO_MIN"


def intervalo_minutos() -> int:
    """Minutos entre corridas. Constante de 5 por omision; la variable de entorno solo la sobreescribe."""
    crudo = os.environ.get(INTERVALO_ENV)
    if crudo is None or not crudo.strip():
        return INTERVALO_MINUTOS_POR_OMISION
    try:
        valor = int(crudo)
    except ValueError:
        return INTERVALO_MINUTOS_POR_OMISION
    return valor if 1 <= valor <= 60 else INTERVALO_MINUTOS_POR_OMISION


def rango_de_las_claves_frecuentes(ahora: datetime) -> tuple[date, date]:
    """`(inicio, fin)` con el que la corrida de 5 minutos llama a los KPIs de `KPIS_FRECUENTES`.

    `ahora` es la hora de pared del negocio (`app.utils.tiempo.ahora_negocio()`), no la del contenedor. Fuera de la primera hora del dia es `(hoy, hoy)`; de las
    00:00:00 a las 00:59:59 es `(ayer, hoy)`. `fin` es siempre hoy: las fotos (en turno, sin salida, en turno por empleado) solo miran `fin`, asi que no cambian; las
    entradas y las salidas recalculan los dos dias.
    """
    hoy = ahora.date()
    if ahora.hour < HORAS_CON_AYER_TRAS_MEDIANOCHE:
        return hoy - timedelta(days=1), hoy
    return hoy, hoy
