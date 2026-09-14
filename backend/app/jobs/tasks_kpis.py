from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.jobs.celery_app import celery
from app.jobs.task_helpers import result_ok
from app.kpis.registry import DIMENSION_JSON_KEY, KPI_REGISTRY
from app.models.kpi_definition import KpiDefinition
from app.models.kpi_snapshot import KpiSnapshot
from app.models.proyect import Proyect
from app.models.session import transaction_context

# Ventana de 7 dias (hoy incluido) para que una factura corregida un par de
# dias despues tambien se refleje, no solo el dia exacto en que se calculo.
VENTANA_DIAS = 7


def _recalcular_kpi_snapshots_en_sesion(session, fecha_inicio: date, fecha_fin: date) -> int:
    """El calculo real, sobre una sesion/transaccion ya abierta.

    Extraido de `recalculate_kpi_snapshots` para que el rango de fechas sea un
    parametro y no algo hardcodeado dentro de la tarea: la tarea nocturna sigue
    llamando esto con su ventana rodante de 7 dias (sin cambio de
    comportamiento), y un backfill manual -- para un lote de prueba sembrado
    con fechas pasadas, que la ventana rodante nunca alcanza -- puede llamarlo
    con cualquier rango arbitrario.
    """
    filas_escritas = 0
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

        # Que llave de `dimension_key` le toca a la entidad que este KPI
        # desglosa ("id_user"/"id_product"/nada si es "global" -- ver
        # DIMENSION_JSON_KEY en app/kpis/registry.py).
        campo_entidad = DIMENSION_JSON_KEY.get(kpi.dimensiones[0], "id_user")

        # Los KPIs SIN alcance de proyecto (`alcance_proyecto=False`) miden
        # entidades que no tienen `id_proyect` en NINGUN punto de la cadena
        # (Incident, InventoryAsset/InventoryLot/InventoryStock, etc.): se
        # calculan UNA SOLA VEZ, no una vez por proyecto activo. Antes este
        # bucle llamaba a `kpi.query_builder` por cada proyecto activo SIN
        # revisar `alcance_proyecto`, y como esos query_builder ignoran
        # `actor_project` a proposito (ver su docstring), el resultado se
        # sembraba identico N veces -- una por proyecto activo- con un
        # `id_proyect` distinto cada vez en `dimension_key`. `routes/kpi.py`
        # ya no filtra por proyecto para estos KPIs (mismo `alcance_proyecto`),
        # asi que sumaba las N copias: el total salia multiplicado por el
        # numero de proyectos activos. Se corrige aqui, calculando una sola
        # vez y sin escribir `id_proyect` en el snapshot para estos KPIs.
        proyectos_a_iterar = proyectos_activos if kpi.alcance_proyecto else [None]

        for id_proyect in proyectos_a_iterar:
            filas = kpi.query_builder(session, fecha_inicio, fecha_fin, {}, id_proyect)
            for id_entidad, periodo, valor in filas:
                dimension_key = {}
                if id_proyect is not None:
                    dimension_key["id_proyect"] = id_proyect
                if campo_entidad is not None:
                    dimension_key[campo_entidad] = id_entidad
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

    return filas_escritas


@celery.task(name="app.jobs.tasks_kpis.recalculate_kpi_snapshots")
def recalculate_kpi_snapshots() -> dict:
    fecha_fin = date.today()
    fecha_inicio = fecha_fin - timedelta(days=VENTANA_DIAS - 1)

    with transaction_context() as session:
        filas_escritas = _recalcular_kpi_snapshots_en_sesion(session, fecha_inicio, fecha_fin)

    return result_ok(
        "jobs.kpis.snapshots_recalculated",
        filas=filas_escritas,
        fecha_inicio=fecha_inicio.isoformat(),
        fecha_fin=fecha_fin.isoformat(),
    )


def recalcular_kpi_snapshots_rango(fecha_inicio: date, fecha_fin: date) -> dict:
    """Invocacion manual: mismo calculo, un rango de fechas arbitrario.

    Para backfills -- p.ej. poblar `kpi_snapshot` para un lote de prueba
    sembrado con fechas pasadas, que la tarea nocturna (ventana rodante de 7
    dias) nunca cubre. No pasa por Celery: se llama directo, igual que ya
    hacen las pruebas con `recalculate_kpi_snapshots()`.
    """
    with transaction_context() as session:
        filas_escritas = _recalcular_kpi_snapshots_en_sesion(session, fecha_inicio, fecha_fin)

    return result_ok(
        "jobs.kpis.snapshots_recalculated",
        filas=filas_escritas,
        fecha_inicio=fecha_inicio.isoformat(),
        fecha_fin=fecha_fin.isoformat(),
    )
