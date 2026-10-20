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

Sin imports pesados a proposito: `app/jobs/beat_schedule.py` lo lee al arrancar el beat.
"""

from __future__ import annotations

import os

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
