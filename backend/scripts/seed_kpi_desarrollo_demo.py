"""Seed de datos de prueba para desarrollo_por_empleado.

Por que existe
--------------
`desarrollo_por_empleado` (`app/kpis/registry.py`) se calcula sobre `task`,
pero la base de dev solo trae 1 fila en esa tabla -- no alcanza para agrupar
por `owner` ni para ver un porcentaje que no sea 0% o 100%. Reutiliza los
mismos 3 usuarios de prueba que `seed_kpi_ventas_egresos_demo.py`
(`kpi-demo-ventas-1/2/3`) y el proyecto bootstrap (`id_proyect=1`, el mismo
que usa ese seed y el unico activo en un dev recien levantado), para que
ambos KPIs de empleado se puedan probar con el mismo lote de actores.

Es idempotente: se detecta por `title` (el campo lo deja libre el flujo
normal de captura, asi que sirve de marcador sin invadir una columna real de
negocio) y si ya corrio antes no vuelve a insertar.
"""

from __future__ import annotations

import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select

from app.models import Proyect, Task, User
from app.models.session import transaction_context

ADMIN_ID = 1
PROYECTO_ID = 1
TITLE_MARCADOR = "Seed demo KPI desarrollo"
USUARIOS_DEMO = ("kpi-demo-ventas-1", "kpi-demo-ventas-2", "kpi-demo-ventas-3")
# Catalogo real de Task.task_status (app/services/operations_workflow.py,
# TASK_STATUSES). Se sortean con pesos para que "terminada" no quede ni en 0%
# ni en 100% para ningun empleado.
TASK_STATUS_PESOS = (
    ("terminada", 5), ("en_proceso", 2), ("bloqueada", 1), ("en_revision", 1), ("cancelada", 1),
)
NUM_TAREAS = 24
DIAS_RANGO = 56  # mismo rango que seed_kpi_ventas_egresos_demo.py


def _first_or_create(db, model, filters, values):
    item = db.scalars(select(model).filter_by(**filters)).first()
    if item:
        return item
    item = model(**values)
    db.add(item)
    db.flush()
    return item


def seed_kpi_desarrollo_demo():
    with transaction_context() as db:
        proyecto = db.get(Proyect, PROYECTO_ID)
        if proyecto is None or proyecto.deletion_date is not None:
            raise RuntimeError(
                f"Falta el proyecto bootstrap (id_proyect={PROYECTO_ID}) o esta dado de baja; "
                "corre init_db.py primero."
            )

        usuarios = []
        for username in USUARIOS_DEMO:
            usuario = db.scalars(select(User).filter_by(username=username)).first()
            if usuario is None:
                raise RuntimeError(
                    f"Falta el usuario de prueba '{username}'; corre primero "
                    "scripts/seed_kpi_ventas_egresos_demo.py."
                )
            usuarios.append(usuario)

        existentes = db.scalars(select(Task).where(Task.title == TITLE_MARCADOR)).all()
        if existentes:
            fechas = [tarea.creation_date for tarea in existentes]
            return {
                "usuarios": [u.id_user for u in usuarios],
                "tareas_creadas": 0,
                "tareas_ya_existentes": len(existentes),
                "rango_fechas": (min(fechas).date().isoformat(), max(fechas).date().isoformat()),
            }

        hoy = datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)
        inicio_rango = hoy - timedelta(days=DIAS_RANGO)

        rng = random.Random(20260908)
        estatus_pool = [status for status, peso in TASK_STATUS_PESOS for _ in range(peso)]
        tareas = []
        for i in range(NUM_TAREAS):
            fecha = inicio_rango + timedelta(
                days=rng.randint(0, DIAS_RANGO), hours=rng.randint(8, 18), minutes=rng.randint(0, 59),
            )
            empleado = usuarios[i % len(usuarios)]
            tareas.append(Task(
                task_description=f"Tarea demo KPI desarrollo #{i + 1}",
                title=TITLE_MARCADOR,
                owner=empleado.id_user,
                dependency=0,
                validation=ADMIN_ID,
                task_status=rng.choice(estatus_pool),
                id_proyect=proyecto.id_proyect,
                created_by=ADMIN_ID,
                creation_date=fecha,
            ))
        db.add_all(tareas)
        db.flush()

        fechas = [tarea.creation_date for tarea in tareas]
        return {
            "usuarios": [u.id_user for u in usuarios],
            "tareas_creadas": len(tareas),
            "tareas_ya_existentes": 0,
            "rango_fechas": (min(fechas).date().isoformat(), max(fechas).date().isoformat()),
        }


if __name__ == "__main__":
    print(seed_kpi_desarrollo_demo())
