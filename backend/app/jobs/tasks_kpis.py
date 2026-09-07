from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.jobs.celery_app import celery
from app.jobs.task_helpers import result_ok
from app.kpis.registry import KPI_REGISTRY
from app.models.kpi_definition import KpiDefinition
from app.models.kpi_snapshot import KpiSnapshot
from app.models.proyect import Proyect
from app.models.session import transaction_context

# Ventana de 7 dias (hoy incluido) para que una factura corregida un par de
# dias despues tambien se refleje, no solo el dia exacto en que se calculo.
VENTANA_DIAS = 7


@celery.task(name="app.jobs.tasks_kpis.recalculate_kpi_snapshots")
def recalculate_kpi_snapshots() -> dict:
    fecha_fin = date.today()
    fecha_inicio = fecha_fin - timedelta(days=VENTANA_DIAS - 1)

    filas_escritas = 0
    with transaction_context() as session:
        id_kpi_definition_por_clave = {
            clave: id_kpi_definition
            for id_kpi_definition, clave in session.execute(
                select(KpiDefinition.id_kpi_definition, KpiDefinition.clave)
            )
        }
        proyectos_activos = session.scalars(
            select(Proyect.id_proyect).where(Proyect.deletion_date.is_(None))
        ).all()

        for kpi in KPI_REGISTRY:
            id_kpi_definition = id_kpi_definition_por_clave.get(kpi.clave)
            if id_kpi_definition is None:
                # kpi_definition todavia no trae esta clave (la siembra de
                # init_db.py no ha corrido en esta base): se salta este KPI en
                # vez de reventar la tarea completa por uno solo.
                continue

            for id_proyect in proyectos_activos:
                filas = kpi.query_builder(session, fecha_inicio, fecha_fin, {}, id_proyect)
                for id_empleado, periodo, valor in filas:
                    dimension_key = {"id_user": id_empleado, "id_proyect": id_proyect}
                    insercion = pg_insert(KpiSnapshot).values(
                        id_kpi_definition=id_kpi_definition,
                        dimension_key=dimension_key,
                        periodo=periodo,
                        valor=valor,
                    )
                    upsert = insercion.on_conflict_do_update(
                        constraint="uq_kpi_snapshot_dia",
                        set_={"valor": insercion.excluded.valor, "computed_at": func.now()},
                    )
                    session.execute(upsert)
                    filas_escritas += 1

    return result_ok(
        "jobs.kpis.snapshots_recalculated",
        filas=filas_escritas,
        fecha_inicio=fecha_inicio.isoformat(),
        fecha_fin=fecha_fin.isoformat(),
    )
