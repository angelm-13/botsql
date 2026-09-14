"""Recalcula kpi_snapshot para un rango de fechas arbitrario.

Por que existe
--------------
`recalculate_kpi_snapshots` (`app/jobs/tasks_kpis.py`) es la tarea nocturna
que mantiene `kpi_snapshot` al dia con una ventana rodante de 7 dias. Sirve
para produccion, pero no para poblar el historico de un lote de prueba que ya
esta sembrado con fechas pasadas (ver `seed_kpi_ventas_egresos_demo.py`): ese
lote nunca cae dentro de los ultimos 7 dias, asi que la tarea nocturna nunca
lo toca.

Este script llama a la misma logica de calculo
(`recalcular_kpi_snapshots_rango`) con un rango de fechas explicito, para
poder ver los KPIs con datos reales sin esperar a que el calendario alcance
la ventana rodante.

Uso
---
    python scripts/recalculate_kpi_snapshots_range.py 2026-07-16 2026-09-08
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.jobs.tasks_kpis import recalcular_kpi_snapshots_rango


def main():
    if len(sys.argv) != 3:
        print("Uso: python scripts/recalculate_kpi_snapshots_range.py <fecha_inicio:YYYY-MM-DD> <fecha_fin:YYYY-MM-DD>")
        sys.exit(1)
    fecha_inicio = date.fromisoformat(sys.argv[1])
    fecha_fin = date.fromisoformat(sys.argv[2])
    if fecha_fin < fecha_inicio:
        print("fecha_fin no puede ser anterior a fecha_inicio")
        sys.exit(1)
    resultado = recalcular_kpi_snapshots_rango(fecha_inicio, fecha_fin)
    print(resultado)


if __name__ == "__main__":
    main()
