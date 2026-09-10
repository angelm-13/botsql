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
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import case, func, or_, select, text

from app.models.document import Document
from app.models.incident import Incident
from app.models.invoice import Invoice
from app.models.laboratory import LaboratoryServiceOrder
from app.models.nm_incident_product import NmIncidentProduct
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


def vales_vencidos_por_responsable_query(session, fecha_inicio, fecha_fin, filtros_dimension, actor_project):
    """Vales (renglones de `NmIncidentProduct`) vencidos y sin cerrar, por responsable.

    * Responsable: `Incident.id_user` -- el vale (un `Incident`) le
      pertenece a quien lo levanto, no a quien cierra cada renglon.
    * Vigencia "vencido": el MISMO filtro, palabra por palabra, que ya usa
      `warehouse_voucher_service.vales_vencidos()` en produccion --
      `deletion_date IS NULL, close_date IS NULL, due_date IS NOT NULL,
      due_date < ahora`. No se reinventa el criterio de "vencido", se reusa
      el que ya esta probado.
    * Rango de fechas: se agrupa por el DIA de `due_date` que cae en
      `[fecha_inicio, fecha_fin]` -- "vales cuyo vencimiento cayo en esta
      ventana". El estado abierto/vencido en si se evalua SIEMPRE contra el
      momento real (`ahora`), nunca contra `fecha_fin`: un vale vencido hace
      3 dias que sigue sin cerrarse cuenta ese dia cada vez que se recalcula,
      igual que la ventana rodante de `recalculate_kpi_snapshots` espera.
    * Sin alcance de proyecto: ni `Incident` ni `NmIncidentProduct` (ni
      `Product`, revisado) tienen `id_proyect` en ningun punto de la cadena
      -- un vale es una operacion interna de almacen, no le pertenece a un
      proyecto de cliente. Por eso este KPI se declara con
      `alcance_proyecto=False`: `tasks_kpis.py` lo calcula una sola vez (no
      una vez por proyecto activo) y `actor_project` se ignora aqui a
      proposito.
    """
    ahora = datetime.now()
    fecha_col = func.date(NmIncidentProduct.due_date)
    condiciones = [
        NmIncidentProduct.deletion_date.is_(None),
        NmIncidentProduct.close_date.is_(None),
        NmIncidentProduct.due_date.isnot(None),
        NmIncidentProduct.due_date < ahora,
        fecha_col >= fecha_inicio,
        fecha_col <= fecha_fin,
    ]

    empleados = (filtros_dimension or {}).get("empleados")
    if empleados:
        condiciones.append(Incident.id_user.in_(empleados))

    stmt = (
        select(Incident.id_user, fecha_col.label("fecha"), func.count())
        .select_from(NmIncidentProduct)
        .join(Incident, Incident.id_incident == NmIncidentProduct.id_incident)
        .where(*condiciones)
        .group_by(Incident.id_user, fecha_col)
        .order_by(Incident.id_user, fecha_col)
    )
    return session.execute(stmt).all()


# "cancelada" NO cuenta como resuelto -- decision explicita de Aurora: un
# incidente cancelado se descarto, no se atendio. Solo resuelta/cerrada.
INCIDENT_RESOLVED_STATUSES = {"resuelta", "cerrada"}


def incidentes_resueltos_por_empleado_query(session, fecha_inicio, fecha_fin, filtros_dimension, actor_project):
    """Porcentaje de incidentes resueltos por empleado responsable (`Incident.id_user`).

    * Vigencia: `Incident.deletion_date IS NULL`.
    * Rango de fechas: `Incident.creation_date` -- mismo campo y mismo
      criterio que `Task.creation_date` en `desarrollo_por_empleado_query`:
      `incident_date` es opcional y no siempre lo puebla la captura (ver
      `incident_service._validate_dates`, puede quedar en NULL), asi que no
      es un campo de fecha confiable para acotar el universo.
    * Formula: `COUNT(incident_status IN (resuelta, cerrada)) / COUNT(*)`
      por `id_user`, sobre los incidentes CREADOS en el rango. El
      denominador incluye cualquier estatus (`abierta`, `en_proceso`,
      `cancelada`, etc.) -- mismo criterio que `desarrollo_por_empleado_query`:
      son incidentes que existieron y no se resolvieron, no se excluyen del
      universo.
    * "cancelada" NO cuenta como resuelto (ver `INCIDENT_RESOLVED_STATUSES`)
      -- decision explicita de Aurora: un incidente cancelado se descarto,
      no se atendio.
    * Sin alcance de proyecto, mismo motivo que
      `vales_vencidos_por_responsable_query`: `Incident` no tiene
      `id_proyect`.
    """
    fecha_col = func.date(Incident.creation_date)
    condiciones = [
        Incident.deletion_date.is_(None),
        fecha_col >= fecha_inicio,
        fecha_col <= fecha_fin,
    ]

    empleados = (filtros_dimension or {}).get("empleados")
    if empleados:
        condiciones.append(Incident.id_user.in_(empleados))

    resueltos = func.sum(case((Incident.incident_status.in_(INCIDENT_RESOLVED_STATUSES), 1), else_=0))
    total = func.count(Incident.id_incident)

    stmt = (
        select(Incident.id_user, resueltos, total)
        .where(*condiciones)
        .group_by(Incident.id_user)
        .order_by(Incident.id_user)
    )

    filas = []
    for id_user, resueltos_usuario, total_usuario in session.execute(stmt).all():
        if not total_usuario:
            continue
        porcentaje = (Decimal(resueltos_usuario) * 100 / Decimal(total_usuario)).quantize(Decimal("0.01"))
        filas.append((id_user, fecha_fin, porcentaje))
    return filas


def cancelaciones_por_empleado_query(session, fecha_inicio, fecha_fin, filtros_dimension, actor_project):
    """Incidentes cancelados por empleado responsable, por dia de cancelacion.

    KPI separado de `incidentes_resueltos_por_empleado_query` a proposito --
    para poder ver picos de cancelaciones por empleado sin que se disuelvan
    en un porcentaje junto con las resoluciones reales.

    * Cancelado: `incident_status == "cancelada"`.
    * Fecha: `close_date`, NO `creation_date` -- `close_date` solo se llena
      en el momento en que el estatus pasa a un estado cerrado (ver
      `incident_service._validate_dates`: si el nuevo estatus esta en
      `INCIDENT_CLOSED_STATUSES` y no traia `close_date`, se completa con
      `ahora`), y "cancelada" es uno de esos estados
      (`operations_workflow.INCIDENT_CLOSED_STATUSES`). Un incidente pudo
      crearse hace meses y cancelarse hoy -- lo que este KPI quiere ver es
      CUANDO se dispararon las cancelaciones, no cuando se abrio el
      incidente.
    * Sin alcance de proyecto, mismo motivo que
      `vales_vencidos_por_responsable_query`.
    """
    fecha_col = func.date(Incident.close_date)
    condiciones = [
        Incident.deletion_date.is_(None),
        Incident.incident_status == "cancelada",
        Incident.close_date.isnot(None),
        fecha_col >= fecha_inicio,
        fecha_col <= fecha_fin,
    ]

    empleados = (filtros_dimension or {}).get("empleados")
    if empleados:
        condiciones.append(Incident.id_user.in_(empleados))

    stmt = (
        select(Incident.id_user, fecha_col.label("fecha"), func.count())
        .where(*condiciones)
        .group_by(Incident.id_user, fecha_col)
        .order_by(Incident.id_user, fecha_col)
    )
    return session.execute(stmt).all()


# Unico estado terminal de exito real en ORDER_STATUSES
# (`app/services/laboratory_service.py`) -- "cancelled" es el otro
# terminal, y no representa una entrega.
LABORATORY_DELIVERED_STATUS = "delivered"


def ordenes_laboratorio_entregadas_por_tecnico_query(session, fecha_inicio, fecha_fin, filtros_dimension, actor_project):
    """Ordenes de servicio de laboratorio entregadas, por tecnico responsable.

    * Vigencia: `deletion_date IS NULL`, `status == "delivered"`.
    * Tecnico: `id_technician` (nullable -- una orden sin tecnico asignado
      no puede contar "por tecnico"; se descarta con IS NOT NULL, mismo
      criterio que `_totales()` en `routes/kpi.py` usa para `id_user is not
      None`).
    * Fecha: `actual_delivery_date` (solo se puebla cuando la orden
      efectivamente se entrega), NO `reception_date` (cuando entro la
      orden, no cuando se resolvio).
    * Alcance: `LaboratoryServiceOrder.id_proyect` existe (columna real,
      NOT NULL) -- este KPI SI tiene alcance por proyecto, igual que
      `ventas_por_empleado_query`.
    """
    fecha_col = func.date(LaboratoryServiceOrder.actual_delivery_date)
    condiciones = [
        LaboratoryServiceOrder.deletion_date.is_(None),
        LaboratoryServiceOrder.status == LABORATORY_DELIVERED_STATUS,
        LaboratoryServiceOrder.id_technician.isnot(None),
        fecha_col >= fecha_inicio,
        fecha_col <= fecha_fin,
    ]

    empleados = (filtros_dimension or {}).get("empleados")
    if empleados:
        condiciones.append(LaboratoryServiceOrder.id_technician.in_(empleados))
    if actor_project is not None:
        condiciones.append(LaboratoryServiceOrder.id_proyect == actor_project)

    stmt = (
        select(LaboratoryServiceOrder.id_technician, fecha_col.label("fecha"), func.count())
        .where(*condiciones)
        .group_by(LaboratoryServiceOrder.id_technician, fecha_col)
        .order_by(LaboratoryServiceOrder.id_technician, fecha_col)
    )
    return session.execute(stmt).all()


def tiempo_promedio_reparacion_laboratorio_por_tecnico_query(session, fecha_inicio, fecha_fin, filtros_dimension, actor_project):
    """Dias promedio de reparacion (`actual_delivery_date - reception_date`), por tecnico.

    Mismas condiciones de vigencia/alcance que
    `ordenes_laboratorio_entregadas_por_tecnico_query` -- ver ese docstring
    para el detalle de por que `status == "delivered"`, `id_technician IS
    NOT NULL` y el alcance por proyecto. Se agrupa por el DIA de entrega
    (`actual_delivery_date`): "de las ordenes entregadas ESE dia, cuanto se
    tardaron en promedio desde que entraron".
    """
    fecha_col = func.date(LaboratoryServiceOrder.actual_delivery_date)
    dias_reparacion = func.extract(
        "epoch", LaboratoryServiceOrder.actual_delivery_date - LaboratoryServiceOrder.reception_date
    ) / 86400.0
    condiciones = [
        LaboratoryServiceOrder.deletion_date.is_(None),
        LaboratoryServiceOrder.status == LABORATORY_DELIVERED_STATUS,
        LaboratoryServiceOrder.id_technician.isnot(None),
        fecha_col >= fecha_inicio,
        fecha_col <= fecha_fin,
    ]

    empleados = (filtros_dimension or {}).get("empleados")
    if empleados:
        condiciones.append(LaboratoryServiceOrder.id_technician.in_(empleados))
    if actor_project is not None:
        condiciones.append(LaboratoryServiceOrder.id_proyect == actor_project)

    stmt = (
        select(LaboratoryServiceOrder.id_technician, fecha_col.label("fecha"), func.avg(dias_reparacion))
        .where(*condiciones)
        .group_by(LaboratoryServiceOrder.id_technician, fecha_col)
        .order_by(LaboratoryServiceOrder.id_technician, fecha_col)
    )
    return session.execute(stmt).all()


def costo_promedio_reparacion_laboratorio_por_tecnico_query(session, fecha_inicio, fecha_fin, filtros_dimension, actor_project):
    """Costo promedio (`final_cost`) de las ordenes entregadas, por tecnico.

    Mismas condiciones de vigencia/alcance que
    `ordenes_laboratorio_entregadas_por_tecnico_query`. `final_cost` es
    nullable (una orden entregada sin costo capturado no debe promediar
    como 0), asi que se excluye explicitamente con IS NOT NULL en vez de
    dejar que el AVG de SQL la ignore en silencio -- mas claro que la
    exclusion es real y no un accidente del promedio.
    """
    fecha_col = func.date(LaboratoryServiceOrder.actual_delivery_date)
    condiciones = [
        LaboratoryServiceOrder.deletion_date.is_(None),
        LaboratoryServiceOrder.status == LABORATORY_DELIVERED_STATUS,
        LaboratoryServiceOrder.id_technician.isnot(None),
        LaboratoryServiceOrder.final_cost.isnot(None),
        fecha_col >= fecha_inicio,
        fecha_col <= fecha_fin,
    ]

    empleados = (filtros_dimension or {}).get("empleados")
    if empleados:
        condiciones.append(LaboratoryServiceOrder.id_technician.in_(empleados))
    if actor_project is not None:
        condiciones.append(LaboratoryServiceOrder.id_proyect == actor_project)

    stmt = (
        select(LaboratoryServiceOrder.id_technician, fecha_col.label("fecha"), func.avg(LaboratoryServiceOrder.final_cost))
        .where(*condiciones)
        .group_by(LaboratoryServiceOrder.id_technician, fecha_col)
        .order_by(LaboratoryServiceOrder.id_technician, fecha_col)
    )
    return session.execute(stmt).all()


# Solo "signed" cuenta como documento vigente que puede vencer -- decision
# explicita de Aurora: "draft" nunca se termino de generar, "issued" es un
# paso intermedio antes de estar vigente (no cuenta como en uso), y
# "rejected"/"cancelled" no representan un documento vigente. Estados reales
# confirmados en `app/services/document_service.py` (DOCUMENT_STATUSES).
DOCUMENT_EXPIRABLE_STATUS = "signed"


def documentos_vencidos_por_responsable_query(session, fecha_inicio, fecha_fin, filtros_dimension, actor_project):
    """Documentos firmados y ya vencidos, por responsable (`created_by`).

    * Vigencia: `deletion_date IS NULL`, `status == "signed"` (ver
      `DOCUMENT_EXPIRABLE_STATUS`).
    * Vencido: `expiration_date` (columna `Date`, no `DateTime`) < HOY real
      (`date.today()`), evaluado siempre contra el momento real -- mismo
      criterio que `vales_vencidos_por_responsable_query`: un documento
      vencido hace 3 dias sigue vencido hoy, sin importar que dia se
      recalcule.
    * Rango de fechas: se agrupa por el DIA de `expiration_date` que cae en
      `[fecha_inicio, fecha_fin]` -- "documentos cuyo vencimiento cayo en
      esta ventana y siguen vencidos hoy".
    * Alcance: `Document.id_proyect` existe (columna real, NOT NULL) --
      este KPI SI tiene alcance por proyecto.
    """
    hoy = date.today()
    condiciones = [
        Document.deletion_date.is_(None),
        Document.status == DOCUMENT_EXPIRABLE_STATUS,
        Document.expiration_date.isnot(None),
        Document.expiration_date < hoy,
        Document.expiration_date >= fecha_inicio,
        Document.expiration_date <= fecha_fin,
    ]

    empleados = (filtros_dimension or {}).get("empleados")
    if empleados:
        condiciones.append(Document.created_by.in_(empleados))
    if actor_project is not None:
        condiciones.append(Document.id_proyect == actor_project)

    stmt = (
        select(Document.created_by, Document.expiration_date, func.count())
        .where(*condiciones)
        .group_by(Document.created_by, Document.expiration_date)
        .order_by(Document.created_by, Document.expiration_date)
    )
    return session.execute(stmt).all()


class KpiDefinition:
    def __init__(self, clave, etiqueta, modulo, dimensiones,
                 query_builder, unidad="numero", alcance_proyecto=True):
        self.clave = clave
        self.etiqueta = etiqueta
        self.modulo = modulo               # clave de MODULOS en app/modules/registry.py
        self.dimensiones = dimensiones      # tupla, ej. ("empleado",)
        self.query_builder = query_builder  # ver firma de ventas_por_empleado_query
        self.unidad = unidad
        # Si el KPI se calcula UNA VEZ POR PROYECTO ACTIVO (True, el default
        # -- lo que ya hacian los primeros 3 KPIs, todos sobre entidades que
        # SI tienen id_proyect) o UNA SOLA VEZ, sin filtro de proyecto
        # (False -- entidades como Incident/NmIncidentProduct que no tienen
        # id_proyect en ningun punto de la cadena). Lo consumen
        # `app/jobs/tasks_kpis.py` (para no llamar N veces al query_builder
        # de un KPI sin proyecto, lo que sembraria N filas identicas en
        # kpi_snapshot) y `app/routes/kpi.py` (para no aplicarle el filtro
        # `dimension_key.id_proyect` de `_totales()`, que dejaria a
        # cualquier no-superusuario viendo cero filas). Ver el docstring de
        # `vales_vencidos_por_responsable_query` para el caso real que
        # motivo este campo -- ya anticipado en el comentario de
        # `actor_project` en `routes/kpi.py` antes de que existiera.
        self.alcance_proyecto = alcance_proyecto


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
    KpiDefinition(
        clave="vales_vencidos_por_responsable",
        etiqueta="Vales vencidos por responsable",
        modulo="operaciones",
        dimensiones=("empleado",),
        query_builder=vales_vencidos_por_responsable_query,
        unidad="numero",
        alcance_proyecto=False,
    ),
    KpiDefinition(
        clave="incidentes_resueltos_por_empleado",
        etiqueta="Incidentes resueltos por empleado",
        modulo="operaciones",
        dimensiones=("empleado",),
        query_builder=incidentes_resueltos_por_empleado_query,
        unidad="porcentaje",
        alcance_proyecto=False,
    ),
    KpiDefinition(
        clave="cancelaciones_por_empleado",
        etiqueta="Cancelaciones por empleado",
        modulo="operaciones",
        dimensiones=("empleado",),
        query_builder=cancelaciones_por_empleado_query,
        unidad="numero",
        alcance_proyecto=False,
    ),
    KpiDefinition(
        clave="ordenes_laboratorio_entregadas_por_tecnico",
        etiqueta="Órdenes de laboratorio entregadas por técnico",
        modulo="laboratorio",
        dimensiones=("empleado",),
        query_builder=ordenes_laboratorio_entregadas_por_tecnico_query,
        unidad="numero",
    ),
    KpiDefinition(
        clave="tiempo_promedio_reparacion_laboratorio_por_tecnico",
        etiqueta="Tiempo promedio de reparación por técnico",
        modulo="laboratorio",
        dimensiones=("empleado",),
        query_builder=tiempo_promedio_reparacion_laboratorio_por_tecnico_query,
        unidad="dias",
    ),
    KpiDefinition(
        clave="costo_promedio_reparacion_laboratorio_por_tecnico",
        etiqueta="Costo promedio de reparación por técnico",
        modulo="laboratorio",
        dimensiones=("empleado",),
        query_builder=costo_promedio_reparacion_laboratorio_por_tecnico_query,
        unidad="moneda",
    ),
    KpiDefinition(
        clave="documentos_vencidos_por_responsable",
        etiqueta="Documentos vencidos por responsable",
        modulo="documentos",
        dimensiones=("empleado",),
        query_builder=documentos_vencidos_por_responsable_query,
        unidad="numero",
    ),
)


# `id_kpi_definition` en `kpi_snapshot`/las rutas es un entero de BD -- este
# mapa resuelve `alcance_proyecto` a partir de la `clave` de KpiDefinition
# (la fila real de `kpi_definition` trae `clave`, sembrada 1 a 1 desde este
# registro). Lo consumen `app/jobs/tasks_kpis.py` y `app/routes/kpi.py`, ver
# el comentario de `KpiDefinition.alcance_proyecto`.
ALCANCE_PROYECTO_POR_CLAVE = {kpi.clave: kpi.alcance_proyecto for kpi in KPI_REGISTRY}


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
