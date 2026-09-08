"""Catalogo de KPIs predefinidos: el usuario los parametriza, no los crea.

Por que existe
--------------
Un KPI no es una fila que alguien arma desde cero: que se mide y como se
calcula es codigo, declarado aqui en `KPI_REGISTRY`. Lo unico que un usuario
elige por KPI es su parametrizacion -- rango de fechas, que empleados, que
tipo de grafica-- que se guarda aparte, en `kpi_dashboard_widget.parametros`.

`KpiDefinition` en este archivo es el descriptor en codigo de un indicador
(clave, etiqueta, que query lo calcula). No confundir con el modelo
SQLAlchemy homonimo `app.models.kpi_definition.KpiDefinition`, que es la fila
de catalogo en la base -- una por cada entrada de `KPI_REGISTRY`, sembrada por
`seed_kpi_definitions()` en cada arranque.

Como se valida
---------------
Igual que `app/modules/registry.py`: `_validar()` revienta al importar si dos
KPIs comparten clave o si alguno declara un modulo que no existe en
`MODULOS` (`app/modules/registry.py`).
"""

from __future__ import annotations

import json
from decimal import Decimal

from sqlalchemy import case, func, or_, select, text

from app.models.invoice import Invoice
from app.models.task import Task
from app.modules.registry import MODULO_POR_CLAVE


def ventas_por_empleado_query(session, fecha_inicio, fecha_fin, filtros_dimension, actor_project):
    """Ventas facturadas por empleado (`Invoice.created_by`) y por dia.

    Decisiones tomadas contra el codigo real, no supuestas -- ver el reporte
    de la tarea para el detalle de donde se confirmo cada una:

    * Campo de venta: `subtotal`, no `total`. `total` ya trae el IVA sumado
      (`quotation_service.calculate_totals`, `invoice_builder.py`: el total
      es la base gravable mas impuestos menos retenciones), que es dinero que
      se entrega a la autoridad fiscal, no ingreso de la empresa. `subtotal`
      es la suma de los importes de los conceptos antes de impuesto: la venta
      real.
    * Vigencia: se excluyen `invoice_status = 'cotizacion'` (todavia no es una
      venta, es una cotizacion sin convertir -- ver
      `routes/invoice.convert_quotation_invoice`) y
      `invoice_status = 'cancelada'` (mismo criterio que usa
      `invoice_credit_note_service`, que filtra exactamente
      `Invoice.invoice_status != 'cancelada'`). Todo lo demas que deja el
      ciclo de vida (`pendiente`, `parcial`, `pagada`, `timbrada`) es una
      venta vigente.
    * Direccion: `invoice_direction` solo lo puebla la clasificacion de XML
      importado (`invoice_xml_classification.classify_invoice_direction`,
      valores `venta`/`compra`/`sin_clasificar`); una factura de venta
      capturada a mano -el camino normal de CRM, ver `manual_invoice_service`-
      se queda con `invoice_direction` en NULL. Por eso el filtro excluye
      unicamente `'compra'` en vez de exigir `'venta'`: exigirlo dejaria fuera
      casi todas las facturas de venta normales.
    """
    fecha_col = func.date(Invoice.date_emision)
    condiciones = [
        Invoice.deletion_date.is_(None),
        fecha_col >= fecha_inicio,
        fecha_col <= fecha_fin,
        Invoice.invoice_status.notin_(["cotizacion", "cancelada"]),
        or_(Invoice.invoice_direction.is_(None), Invoice.invoice_direction != "compra"),
    ]

    empleados = (filtros_dimension or {}).get("empleados")
    if empleados:
        condiciones.append(Invoice.created_by.in_(empleados))
    if actor_project is not None:
        condiciones.append(Invoice.id_proyect == actor_project)

    stmt = (
        select(Invoice.created_by, fecha_col.label("fecha"), func.sum(Invoice.subtotal))
        .where(*condiciones)
        .group_by(Invoice.created_by, fecha_col)
        .order_by(Invoice.created_by, fecha_col)
    )
    return session.execute(stmt).all()


def egresos_por_empleado_query(session, fecha_inicio, fecha_fin, filtros_dimension, actor_project):
    """Egresos facturados por empleado (`Invoice.created_by`) y por dia.

    Espejo exacto de `ventas_por_empleado_query`: mismo campo de venta
    (`subtotal`, antes de impuesto), misma vigencia (excluye `cotizacion` y
    `cancelada`), mismo agrupamiento y mismo alcance por proyecto. La unica
    diferencia es la direccion: en vez de excluir `invoice_direction ==
    'compra'` (para dejar pasar tambien las facturas de venta capturadas a
    mano, que se quedan con `invoice_direction` en NULL -- ver el docstring de
    `ventas_por_empleado_query`), aqui se exige exactamente `'compra'`. Una
    factura con `invoice_direction` en NULL nunca es un egreso: ese NULL es el
    camino normal de venta manual, no una compra sin clasificar.
    """
    fecha_col = func.date(Invoice.date_emision)
    condiciones = [
        Invoice.deletion_date.is_(None),
        fecha_col >= fecha_inicio,
        fecha_col <= fecha_fin,
        Invoice.invoice_status.notin_(["cotizacion", "cancelada"]),
        Invoice.invoice_direction == "compra",
    ]

    empleados = (filtros_dimension or {}).get("empleados")
    if empleados:
        condiciones.append(Invoice.created_by.in_(empleados))
    if actor_project is not None:
        condiciones.append(Invoice.id_proyect == actor_project)

    stmt = (
        select(Invoice.created_by, fecha_col.label("fecha"), func.sum(Invoice.subtotal))
        .where(*condiciones)
        .group_by(Invoice.created_by, fecha_col)
        .order_by(Invoice.created_by, fecha_col)
    )
    return session.execute(stmt).all()


# Catalogo real de `Task.task_status` (`app/services/operations_workflow.py`,
# `TASK_STATUSES`). No hay CHECK constraint en BD para esta columna -a
# diferencia de `proyect_status`-, asi que en la practica puede traer NULL o
# un valor que ya no este en este catalogo (dato viejo, captura manual antes
# de que existiera la normalizacion). Ninguno de esos casos cuenta como
# avance: decision de Aurora, ver `desarrollo_por_empleado_query`.
TASK_STATUSES_CONOCIDOS = ("pendiente", "en_proceso", "bloqueada", "en_revision", "terminada", "cancelada")


def desarrollo_por_empleado_query(session, fecha_inicio, fecha_fin, filtros_dimension, actor_project):
    """Porcentaje de tareas terminadas por empleado responsable (`Task.owner`).

    * Vigencia: `Task.deletion_date IS NULL`, igual que el resto del modulo de
      operaciones (`project_management_service.py`).
    * Rango de fechas: `Task.creation_date`, el mismo campo que ya usa
      `project_management_service.list_tasks` para ordenar/filtrar tareas de
      un proyecto -- `Task` no tiene otro campo de fecha "de negocio"
      (`start_date` es opcional y no lo puebla el flujo normal de captura).
    * Formula: `COUNT(task_status = 'terminada') / COUNT(*)` por `owner`,
      sobre las tareas vigentes del rango. El denominador incluye cualquier
      estatus (`bloqueada`, `cancelada`, etc.): son tareas que existieron y no
      se completaron, no se excluyen del universo.
    * `task_status` NULL o fuera de `TASK_STATUSES_CONOCIDOS` nunca cuenta
      como `'terminada'` -decision de Aurora-: no se le asume avance a un
      estatus que el sistema no reconoce.
    * Se calcula en Python sobre los conteos crudos (no con una division en
      SQL) para no depender de como cada dialecto castea `SUM`/`COUNT` a
      punto flotante, y para poder devolver `Decimal` igual que
      `ventas_por_empleado_query`.
    * Igual que las demas, regresa una fila por `owner` con `fecha_fin` como
      periodo: es un porcentaje del rango completo, no una serie diaria.
    """
    fecha_col = func.date(Task.creation_date)
    condiciones = [
        Task.deletion_date.is_(None),
        fecha_col >= fecha_inicio,
        fecha_col <= fecha_fin,
    ]

    empleados = (filtros_dimension or {}).get("empleados")
    if empleados:
        condiciones.append(Task.owner.in_(empleados))
    if actor_project is not None:
        condiciones.append(Task.id_proyect == actor_project)

    terminadas = func.sum(case((Task.task_status == "terminada", 1), else_=0))
    total = func.count(Task.id_task)

    stmt = (
        select(Task.owner, terminadas, total)
        .where(*condiciones)
        .group_by(Task.owner)
        .order_by(Task.owner)
    )

    filas = []
    for owner, terminadas_owner, total_owner in session.execute(stmt).all():
        if not total_owner:
            continue
        porcentaje = (Decimal(terminadas_owner) * 100 / Decimal(total_owner)).quantize(Decimal("0.01"))
        filas.append((owner, fecha_fin, porcentaje))
    return filas


class KpiDefinition:
    def __init__(self, clave, etiqueta, modulo, dimensiones,
                 query_builder, unidad="numero"):
        self.clave = clave
        self.etiqueta = etiqueta
        self.modulo = modulo               # clave de MODULOS en app/modules/registry.py
        self.dimensiones = dimensiones      # tupla, ej. ("empleado",)
        self.query_builder = query_builder  # ver firma de ventas_por_empleado_query
        self.unidad = unidad


KPI_REGISTRY = (
    KpiDefinition(
        clave="ventas_por_empleado",
        etiqueta="Ventas por empleado",
        modulo="facturacion",
        dimensiones=("empleado",),
        query_builder=ventas_por_empleado_query,
        unidad="moneda",
    ),
    KpiDefinition(
        clave="egresos_por_empleado",
        etiqueta="Egresos por empleado",
        modulo="facturacion",
        dimensiones=("empleado",),
        query_builder=egresos_por_empleado_query,
        unidad="moneda",
    ),
    KpiDefinition(
        clave="desarrollo_por_empleado",
        etiqueta="Desarrollo por empleado",
        modulo="operaciones",
        dimensiones=("empleado",),
        query_builder=desarrollo_por_empleado_query,
        unidad="porcentaje",
    ),
)


# "tiempo_promedio_atencion" queda pendiente de agregar a este registro.
#
# Se investigo contra el modelo real (`app/models/appointment.py`): hoy
# `Appointment.ends_at` no es un cierre real de la atencion, es
# `starts_at + AppointmentType.duration_minutes` calculado al *crear* la cita
# (`appointment_service.py`, `book_appointment`), asi que `ends_at - starts_at`
# siempre da la duracion nominal configurada por tipo de cita, nunca cuanto
# tardo la atencion real. Tampoco existe un status de cierre: `Appointment.status`
# solo tiene `pending_confirmation` / `confirmed` / `cancelled`, nada como
# `completed`/`attended`/`no_show` que confirme que la cita se llevo a cabo.
#
# Calcular este KPI hoy daria un promedio de duraciones preconfiguradas, no de
# desempeno real -- se veria como un KPI valido pero mediria otra cosa. Antes
# de escribir la query hace falta una decision de producto sobre el modulo de
# citas (agregar un campo real de cierre, ej. `attended_at`/`closed_at`, y un
# estatus de cierre), no una decision de este modulo de KPIs.


def _validar():
    claves = [kpi.clave for kpi in KPI_REGISTRY]
    if len(claves) != len(set(claves)):
        raise RuntimeError("Hay dos KPIs con la misma clave.")
    for kpi in KPI_REGISTRY:
        if kpi.modulo not in MODULO_POR_CLAVE:
            raise RuntimeError(
                f"El KPI '{kpi.clave}' apunta al modulo inexistente '{kpi.modulo}'."
            )


_validar()


def seed_kpi_definitions(engine) -> None:
    """Siembra `kpi_definition` desde `KPI_REGISTRY`.

    Se corre en cada arranque (ver `init_db.py`), igual que el resto de los
    catalogos: la clave es la fuente de verdad, asi que una etiqueta o unidad
    que cambie aqui se refleja sola en la base sin escribir una migracion.
    """
    with engine.begin() as conn:
        for kpi in KPI_REGISTRY:
            conn.execute(
                text(
                    """
                    INSERT INTO kpi_definition (clave, etiqueta, modulo, dimensiones, unidad, created_by)
                    VALUES (:clave, :etiqueta, :modulo, CAST(:dimensiones AS jsonb), :unidad, 1)
                    ON CONFLICT (clave) DO UPDATE SET
                        etiqueta = EXCLUDED.etiqueta,
                        modulo = EXCLUDED.modulo,
                        dimensiones = EXCLUDED.dimensiones,
                        unidad = EXCLUDED.unidad,
                        last_update_date = CURRENT_TIMESTAMP
                    """
                ),
                {
                    "clave": kpi.clave,
                    "etiqueta": kpi.etiqueta,
                    "modulo": kpi.modulo,
                    "dimensiones": json.dumps(list(kpi.dimensiones)),
                    "unidad": kpi.unidad,
                },
            )
