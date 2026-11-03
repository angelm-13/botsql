"""Criterios de filas compartidos por los KPIs.

Vive aparte de `registry.py` y de `modulos/checadas.py` para no crear una importacion circular: `registry.py`
importa el modulo de checadas al final, y las consultas de incidencias de `registry.py` necesitan este criterio.
"""

from __future__ import annotations

from app.kpis.modulos.checadas import es_checada


def no_es_checada():
    """Condicion SQL: la fila de `incident` es una incidencia de verdad, no una checada.

    Una checada es una fila de `incident` con coordenadas (`es_checada()`, la unica que nombra `Incident.latitude`).
    Sin esta condicion, una persona en turno contaba como "incidencia pendiente" y sus entradas y salidas como
    incidencias abiertas y cerradas. Es la negacion de `es_checada()`, no una regla aparte: si cambia como se
    reconoce una checada, este criterio cambia con ella.
    """
    return ~es_checada()
