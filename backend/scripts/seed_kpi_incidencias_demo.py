"""Seed de datos de prueba LOCAL para los KPIs nuevos de incidencias/material
(`incidencias_abiertas_por_empleado`, `incidencias_pendientes`,
`incidencias_abiertas_vs_cerradas`, `material_por_estado`) y de paso da mas
volumen a `incidentes_resueltos_por_empleado`/`cancelaciones_por_empleado`,
que ya existian pero con muy pocas filas en un dev recien levantado.

Por que existe
---------------
Los 4 KPIs nuevos se disenaron para el contexto real de Adser (almacen de
herramientas: importa cuantas incidencias se abren/cierran, cuanto material
esta prestado y en que estado -- no "bajo stock", que no aplica ahi), pero
esta base local no tiene datos de Adser. Sin esto, los widgets de un tablero
de prueba saldrian todos en "Sin datos".

No genera el escenario de `material_prestado_actual` (el KPI en vivo que
sigue bloqueado -- ver el aviso al usuario en esta misma tarea sobre
`nm_incident_product.start_date` vacio en Adser): esta base local es de
prueba, no migrada, asi que no hay ningun problema de datos que simular ahi;
simplemente no hace falta porque ese KPI no se construyo todavia.

Guarda de seguridad
--------------------
Se niega a correr si `DB_HOST` no es un host local conocido. `DB_HOST=db` es
el nombre del servicio de PostgreSQL en `docker-compose.yml` (el unico host
que este script acepta sin pedir nada mas); en k8s el Service de Postgres se
llama `postgres` (`k8s/base/backend.yaml`/`postgres.yaml`), asi que cualquier
ambiente real (tyakxa-dev/torredigital-prod/adser-prod) revienta aqui antes
de escribir una sola fila.

Idempotente: se detecta por `Incident.note == MARCADOR` (mismo patron que
`seed_kpi_desarrollo_demo.py` usa con `Task.title`) y si ya corrio antes no
vuelve a insertar -- solo corre el backfill de `kpi_snapshot` de nuevo (barato
y seguro, upsert).

Uso
---
    docker compose exec backend python -m scripts.seed_kpi_incidencias_demo
"""

from __future__ import annotations

import os
import random
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select  # noqa: E402

from app.jobs.tasks_kpis import recalcular_kpi_snapshots_rango  # noqa: E402
from app.models import Incident, IncidentType, NmIncidentProduct, User  # noqa: E402
from app.models.session import transaction_context  # noqa: E402

HOSTS_LOCALES_PERMITIDOS = {"db", "localhost", "127.0.0.1"}

ADMIN_ID = 1
PRODUCT_ID_BOOTSTRAP = 1  # sembrado por database/seed.sql, existe en cualquier dev local
INCIDENT_TYPE_NORMAL_ID = 1  # idem -- "test description"
MARCADOR = "Seed demo KPI incidencias/material"
USUARIOS_DEMO = ("kpi-demo-incidencias-1", "kpi-demo-incidencias-2", "kpi-demo-incidencias-3")
NUM_INCIDENTES = 40
DIAS_RANGO = 90
# "abierta" pesa igual que resuelta+cerrada+cancelada juntas, para que
# incidencias_pendientes no salga en 0 en ningun dia del rango.
ESTATUS_PESOS = (("resuelta", 3), ("cerrada", 2), ("cancelada", 1), ("abierta", 6))
DIRECTION_PESOS = (("salida", 7), ("entrada", 3))


def _verificar_host_local():
    db_host = os.getenv("DB_HOST", "db")
    if db_host not in HOSTS_LOCALES_PERMITIDOS:
        raise RuntimeError(
            f"DB_HOST='{db_host}' no es un host local conocido "
            f"({', '.join(sorted(HOSTS_LOCALES_PERMITIDOS))}). Este script genera datos de "
            "PRUEBA (incidencias y vales falsos) y se niega a correr fuera del stack local "
            "de docker-compose -- en k8s el servicio de Postgres se llama 'postgres', nunca 'db'."
        )


def _first_or_create(db, model, filters, values):
    item = db.scalars(select(model).filter_by(**filters)).first()
    if item:
        return item
    item = model(**values)
    db.add(item)
    db.flush()
    return item


def seed_kpi_incidencias_demo():
    _verificar_host_local()

    with transaction_context() as db:
        usuarios = []
        for i, username in enumerate(USUARIOS_DEMO):
            usuario = _first_or_create(
                db, User, {"username": username},
                {
                    "username": username, "full_name": f"Empleado demo incidencias {i + 1}",
                    "id_permission": 1, "id_proyect": 1, "id_status": 1, "supervisor": ADMIN_ID,
                    "user_type": "employee", "is_employee": True, "created_by": ADMIN_ID,
                },
            )
            usuarios.append(usuario)

        tipo_destruccion = _first_or_create(
            db, IncidentType, {"incident_type_description": "Destruccion"},
            {"incident_type_description": "Destruccion", "created_by": ADMIN_ID},
        )
        tipo_extraviado = _first_or_create(
            db, IncidentType, {"incident_type_description": "Extraviado"},
            {"incident_type_description": "Extraviado", "created_by": ADMIN_ID},
        )

        existentes = db.scalars(select(Incident).where(Incident.note == MARCADOR)).all()
        if existentes:
            fechas = [i.incident_date for i in existentes if i.incident_date]
            resultado = {
                "usuarios": [u.id_user for u in usuarios],
                "incidentes_creados": 0,
                "incidentes_ya_existentes": len(existentes),
                "rango_fechas": (min(fechas).date().isoformat(), max(fechas).date().isoformat()) if fechas else None,
            }
        else:
            ahora = datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)
            rng = random.Random(20260928)
            estatus_pool = [estado for estado, peso in ESTATUS_PESOS for _ in range(peso)]
            direction_pool = [direccion for direccion, peso in DIRECTION_PESOS for _ in range(peso)]

            incidentes = []
            for i in range(NUM_INCIDENTES):
                dias_atras = rng.randint(0, DIAS_RANGO)
                fecha = ahora - timedelta(days=dias_atras, hours=-rng.randint(0, 10))
                empleado = usuarios[i % len(usuarios)]
                estado = rng.choice(estatus_pool)
                close_date = None
                if estado != "abierta":
                    offset_max = max(0, dias_atras - 1)  # nunca cierra en el futuro
                    offset = rng.randint(0, min(5, offset_max)) if offset_max else 0
                    close_date = fecha + timedelta(days=offset, hours=rng.randint(0, 8))
                    if close_date > ahora:
                        close_date = ahora

                incidentes.append(Incident(
                    id_incident_type=INCIDENT_TYPE_NORMAL_ID,
                    note=MARCADOR,
                    id_user=empleado.id_user,
                    incident_status=estado,
                    incident_date=fecha,
                    close_date=close_date,
                    created_by=ADMIN_ID,
                ))
            db.add_all(incidentes)
            db.flush()

            renglones = []
            for i, incidente in enumerate(incidentes):
                if i % 3 == 2:  # ~1 de cada 3, sin renglon -- no todo vale mueve material
                    continue
                renglones.append(NmIncidentProduct(
                    id_incident=incidente.id_incident, id_product=PRODUCT_ID_BOOTSTRAP,
                    quantity=1, direction=rng.choice(direction_pool), created_by=ADMIN_ID,
                ))

            # 4 vales explicitos de tipo especial, fechados en los ultimos 30
            # dias, para que material_por_estado tenga Destruccion/Extraviado
            # con datos reales y no solo Entrada/Salida.
            especiales = []
            for offset, tipo in ((3, tipo_destruccion), (10, tipo_destruccion), (7, tipo_extraviado), (18, tipo_extraviado)):
                especiales.append(Incident(
                    id_incident_type=tipo.id_incident_type,
                    note=MARCADOR,
                    id_user=usuarios[offset % len(usuarios)].id_user,
                    incident_status="cerrada",
                    incident_date=ahora - timedelta(days=offset),
                    close_date=ahora - timedelta(days=max(offset - 1, 0)),
                    created_by=ADMIN_ID,
                ))
            db.add_all(especiales)
            db.flush()
            for incidente in especiales:
                renglones.append(NmIncidentProduct(
                    id_incident=incidente.id_incident, id_product=PRODUCT_ID_BOOTSTRAP,
                    quantity=1, direction="salida", created_by=ADMIN_ID,
                ))
            db.add_all(renglones)
            db.flush()

            todos = incidentes + especiales
            fechas = [i.incident_date for i in todos]
            resultado = {
                "usuarios": [u.id_user for u in usuarios],
                "incidentes_creados": len(todos),
                "incidentes_ya_existentes": 0,
                "renglones_creados": len(renglones),
                "rango_fechas": (min(fechas).date().isoformat(), max(fechas).date().isoformat()),
            }

    # Backfill de kpi_snapshot para todo el rango -- sin esto los widgets
    # siguen en "Sin datos" aunque ya existan los incidentes/vales: el job
    # nocturno solo cubre una ventana rodante de 7 dias hacia adelante desde
    # que el scheduler arranco (ver app/jobs/tasks_kpis.py), nunca fechas
    # pasadas de un lote sembrado a mano.
    fecha_fin = date.today()
    fecha_inicio = fecha_fin - timedelta(days=DIAS_RANGO + 1)
    backfill = recalcular_kpi_snapshots_rango(fecha_inicio, fecha_fin)
    resultado["backfill"] = backfill
    return resultado


if __name__ == "__main__":
    print(seed_kpi_incidencias_demo())
