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
from app.models.inventory_asset import InventoryAsset, PRESTADA
from app.models.inventory_asset_event import InventoryAssetEvent, PRESTAMO
from app.models.inventory_lot import InventoryLot
from app.models.inventory_stock import InventoryStock
from app.models.invoice import Invoice
from app.models.laboratory import LaboratoryServiceOrder
from app.models.nm_incident_product import NmIncidentProduct
from app.models.task import Task
from app.services.warehouse_voucher_service import CIERRE_SENTINELA
from app.modules.registry import MODULO_POR_CLAVE

# Que llave de `dimension_key` (JSONB, en `kpi_snapshot`) le corresponde a cada
# tipo de dimension declarado en `KpiDefinition.dimensiones`. "global" no
# agrega ninguna llave de entidad -- el KPI no se desglosa por nada, solo
# guarda `id_proyect` cuando aplica (ver `alcance_proyecto`). La consumen
# `app/jobs/tasks_kpis.py` (para saber que llave escribir al insertar el
# snapshot) y `app/routes/kpi.py` (para saber que llave leer al sumar).
DIMENSION_JSON_KEY = {
    "empleado": "id_user",
    "producto": "id_product",
    "global": None,
    # El valor de cada fila no es un id de entidad sino el nombre de una
    # categoria fija (ej. "abierta"/"cerrada", "Entrada"/"Salida"/...) -- ver
    # `incidencias_abiertas_vs_cerradas_query`/`material_por_estado_query`.
    # `_totales()` en routes/kpi.py ya es generico sobre el TIPO del valor
    # que guarda `dimension_key` (siempre lo compara como texto via
    # `.astext`), asi que un string de categoria funciona igual que un id.
    "estado": "estado",
}

# Los 4 niveles de "que tan buena es una variacion" para un KPI, declarados
# por cada uno en `direccion` (ver KpiDefinition): "alto_es_mejor" (ventas,
# resueltos...), "bajo_es_mejor" (vencidos, cancelaciones...) y "neutral"
# cuando mas/menos no es en si bueno ni malo (es solo volumen/actividad,
# ej. material_prestado_por_responsable). La consume el frontend para
# colorear la flecha de variacion del widget de tipo numero -- sin esto,
# "subio" se pintaba siempre de verde sin importar si subir es deseable.
DIRECCIONES = ("alto_es_mejor", "bajo_es_mejor", "neutral")

# Tipos de grafica que existen hoy en el frontend (numero/barras/linea/
# area/dona) mas "tabla" (declarada aqui aunque el renderer de frontend
# todavia no exista -- se agrega con el rediseno del dashboard). Cada KPI
# declara cuales le aplican (`graficas_permitidas`) y cual se preselecciona
# (`grafica_default`).
GRAFICAS = ("numero", "barras", "linea", "area", "dona", "tabla")

# "snapshot": el KPI de siempre -- su query_builder lo llama la tarea
# nocturna (`app/jobs/tasks_kpis.py`) y el backfill manual, y el resultado
# vive en `kpi_snapshot`; declara `agregacion` porque hay que combinar varios
# dias. "vivo": el KPI NO pasa por el job ni por `kpi_snapshot` -- su
# query_builder se llama en el momento de renderizar el widget, sobre datos
# de detalle (ej. cada renglon de un prestamo individual, con su fecha
# exacta) que no caben en "un numero por entidad y dia". No declara
# `agregacion` (no hay nada que combinar entre dias: siempre es "ahora").
MODOS = ("snapshot", "vivo")

# Vocabulario cerrado de unidades -- igual que AGREGACIONES, revienta al
# importar si un KPI declara una que no este aqui. El formato visual de cada
# una (que sufijo/simbolo mostrar) es trabajo del frontend, no de este
# registro -- ver el rediseno del dashboard.
UNIDADES = ("numero", "porcentaje", "moneda", "dias")

# Vocabulario cerrado de dimensiones -- "estado" es nueva (ver
# DIMENSION_JSON_KEY arriba), las otras tres ya existian sin validarse.
DIMENSIONES = ("empleado", "producto", "global", "estado")

# Como se combinan varios snapshots de un KPI (varios dias, varios proyectos)
# en un solo numero -- lo declara cada KPI en `agregacion`, sin valor por
# omision: antes `routes/kpi.py` sumaba SIEMPRE, y eso inflaba en silencio
# cualquier KPI que no fuera un conteo o un monto (30 dias de un 50 % daban
# 1500 %; 30 fotos de 10 piezas en existencia daban 300). Medido contra
# Postgres real al corregirlo.
#
# * "suma": conteos y montos por dia -- sumar dias y proyectos es correcto.
# * "promedio_ponderado": porcentajes y promedios. El `query_builder` regresa
#   una cuarta columna, `peso` (cuantos casos hay detras de ese valor: tareas,
#   incidentes, ordenes), y el total es SUM(valor * peso) / SUM(peso). Sin el
#   peso, promediar los valores diarios le daria el mismo voto a un dia con 1
#   orden que a uno con 50.
# * "ultimo": fotos del estado actual (existencias), no eventos. Cada noche
#   repite la foto completa, asi que sumar dias multiplica; lo correcto es
#   tomar la foto del ultimo dia del rango que tenga datos.
AGREGACIONES = ("suma", "promedio_ponderado", "ultimo")


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
    * Una fila por `owner` y por DIA de creacion, con el numero de tareas de
      ese dia como `peso` (cuarta columna, ver `AGREGACIONES`). Antes era una
      sola fila por `owner` fechada en `fecha_fin` con el porcentaje del rango
      completo: la tarea nocturna la reescribia cada noche con una ventana de
      7 dias distinta, y al sumar esas noches el porcentaje salia multiplicado
      por el numero de dias del rango. Por dia y con peso, el porcentaje de
      cualquier rango se reconstruye exacto (`promedio_ponderado`).
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
        select(Task.owner, fecha_col.label("fecha"), terminadas, total)
        .where(*condiciones)
        .group_by(Task.owner, fecha_col)
        .order_by(Task.owner, fecha_col)
    )

    filas = []
    for owner, fecha, terminadas_owner, total_owner in session.execute(stmt).all():
        if not total_owner:
            continue
        porcentaje = (Decimal(terminadas_owner) * 100 / Decimal(total_owner)).quantize(Decimal("0.01"))
        filas.append((owner, fecha, porcentaje, total_owner))
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
        or_(
            NmIncidentProduct.close_date.is_(None),
            NmIncidentProduct.close_date == CIERRE_SENTINELA,
        ),
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
    * Una fila por `id_user` y por DIA de creacion, con el numero de
      incidentes de ese dia como `peso` -- mismo motivo que
      `desarrollo_por_empleado_query` (`promedio_ponderado`).
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
        select(Incident.id_user, fecha_col.label("fecha"), resueltos, total)
        .where(*condiciones)
        .group_by(Incident.id_user, fecha_col)
        .order_by(Incident.id_user, fecha_col)
    )

    filas = []
    for id_user, fecha, resueltos_usuario, total_usuario in session.execute(stmt).all():
        if not total_usuario:
            continue
        porcentaje = (Decimal(resueltos_usuario) * 100 / Decimal(total_usuario)).quantize(Decimal("0.01"))
        filas.append((id_user, fecha, porcentaje, total_usuario))
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
    * Sentinel heredado: `close_date == CIERRE_SENTINELA` se excluye
      explicitamente, ademas de `IS NOT NULL` -- `CIERRE_SENTINELA` no es un
      cierre real (ver `_sin_cerrar` en warehouse_voucher_service.py), asi
      que un incidente cancelado migrado de Adser sin fecha de cierre
      capturada NO debe contarse como "cancelado el 1990-01-01". Antes de
      este fix, `close_date.isnot(None)` dejaba pasar el sentinel igual que
      una fecha real -- el efecto practico era que esas cancelaciones
      quedaban invisibles en cualquier rango real (nadie pide un reporte que
      incluya 1990), pero el criterio era incorrecto de fondo, no solo
      inofensivo por casualidad.
    """
    fecha_col = func.date(Incident.close_date)
    condiciones = [
        Incident.deletion_date.is_(None),
        Incident.incident_status == "cancelada",
        Incident.close_date.isnot(None),
        Incident.close_date != CIERRE_SENTINELA,
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
    tardaron en promedio desde que entraron". Cuarta columna: cuantas ordenes
    hay detras de ese promedio (`peso`, ver `AGREGACIONES`).
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
        select(LaboratoryServiceOrder.id_technician, fecha_col.label("fecha"), func.avg(dias_reparacion), func.count())
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
    exclusion es real y no un accidente del promedio. Por lo mismo el `peso`
    (cuarta columna) cuenta solo las ordenes CON costo.
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
        select(LaboratoryServiceOrder.id_technician, fecha_col.label("fecha"), func.avg(LaboratoryServiceOrder.final_cost), func.count())
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


def ingresos_totales_query(session, fecha_inicio, fecha_fin, filtros_dimension, actor_project):
    """Ingresos de la empresa (ventas facturadas), por dia, SIN desglose por empleado.

    Mismo criterio de vigencia y campo de venta que `ventas_por_empleado_query`
    -- ver ese docstring para el detalle de por que `subtotal` (no `total`) y
    por que se excluyen `cotizacion`/`cancelada`. La diferencia es el
    proposito: este KPI es la variable "ingresos" pensada para compararse
    contra "egresos" en un mismo grafico (pedido explicito de Aurora), no un
    desglose por responsable -- por eso no se agrupa por `created_by`.

    Dimension "global" (ver `DIMENSION_JSON_KEY`): no hay entidad que
    desglosar, asi que cada fila regresa `None` como primer elemento -- el
    snapshot no guarda ninguna llave de entidad para este KPI, solo
    `id_proyect` cuando aplica.
    """
    fecha_col = func.date(Invoice.date_emision)
    condiciones = [
        Invoice.deletion_date.is_(None),
        fecha_col >= fecha_inicio,
        fecha_col <= fecha_fin,
        Invoice.invoice_status.notin_(["cotizacion", "cancelada"]),
        or_(Invoice.invoice_direction.is_(None), Invoice.invoice_direction != "compra"),
    ]
    if actor_project is not None:
        condiciones.append(Invoice.id_proyect == actor_project)

    stmt = (
        select(fecha_col.label("fecha"), func.sum(Invoice.subtotal))
        .where(*condiciones)
        .group_by(fecha_col)
        .order_by(fecha_col)
    )
    return [(None, fecha, valor) for fecha, valor in session.execute(stmt).all()]


def egresos_totales_query(session, fecha_inicio, fecha_fin, filtros_dimension, actor_project):
    """Egresos de la empresa (facturas de compra), por dia, SIN desglose por empleado.

    Espejo de `ingresos_totales_query`, con el mismo cambio de direccion que
    `egresos_por_empleado_query` frente a `ventas_por_empleado_query` --
    exige `invoice_direction == 'compra'` en vez de excluir solo `'compra'`.
    Ver `ingresos_totales_query` para el resto del criterio (dimension
    "global", sin desglose por responsable).
    """
    fecha_col = func.date(Invoice.date_emision)
    condiciones = [
        Invoice.deletion_date.is_(None),
        fecha_col >= fecha_inicio,
        fecha_col <= fecha_fin,
        Invoice.invoice_status.notin_(["cotizacion", "cancelada"]),
        Invoice.invoice_direction == "compra",
    ]
    if actor_project is not None:
        condiciones.append(Invoice.id_proyect == actor_project)

    stmt = (
        select(fecha_col.label("fecha"), func.sum(Invoice.subtotal))
        .where(*condiciones)
        .group_by(fecha_col)
        .order_by(fecha_col)
    )
    return [(None, fecha, valor) for fecha, valor in session.execute(stmt).all()]


def material_prestado_por_responsable_query(session, fecha_inicio, fecha_fin, filtros_dimension, actor_project):
    """Prestamos de material INICIADOS por dia, por responsable (`id_holder_after`).

    Fuente: `inventory_asset_event` con `event_type = 'prestamo'`, no
    `inventory_asset.status = 'prestada'` -- el estado actual de la pieza
    solo dice DONDE esta hoy, no CUANDO empezo el prestamo (ver el docstring
    de la clase `InventoryAssetEvent`, que explica por que existe esta
    bitacora aparte del estado). Un evento de prestamo trae una fecha real
    (`creation_date`) que si sirve para una serie por dia.

    Responsable: `id_holder_after` -- quien recibio la pieza en ESE evento
    (puede no coincidir con quien la tiene hoy, si ya hubo otro evento
    despues; este KPI mide cuando se prestaron piezas, no el estado actual).

    Sin alcance de proyecto (`alcance_proyecto=False`): un prestamo de
    herramienta es una operacion interna de almacen, igual que un vale de
    almacen -- ver el docstring de `vales_vencidos_por_responsable_query`,
    mismo motivo: ni `inventory_asset_event` ni `inventory_asset` ni
    `product` tienen `id_proyect` en la cadena.
    """
    fecha_col = func.date(InventoryAssetEvent.creation_date)
    condiciones = [
        InventoryAssetEvent.event_type == PRESTAMO,
        InventoryAssetEvent.id_holder_after.isnot(None),
        fecha_col >= fecha_inicio,
        fecha_col <= fecha_fin,
    ]

    empleados = (filtros_dimension or {}).get("empleados")
    if empleados:
        condiciones.append(InventoryAssetEvent.id_holder_after.in_(empleados))

    stmt = (
        select(InventoryAssetEvent.id_holder_after, fecha_col.label("fecha"), func.count())
        .where(*condiciones)
        .group_by(InventoryAssetEvent.id_holder_after, fecha_col)
        .order_by(InventoryAssetEvent.id_holder_after, fecha_col)
    )
    return session.execute(stmt).all()


def prestamos_vencidos_por_responsable_query(session, fecha_inicio, fecha_fin, filtros_dimension, actor_project):
    """Piezas prestadas y ya vencidas (`due_date` pasado), por responsable actual.

    Mismo criterio, palabra por palabra, que
    `vales_vencidos_por_responsable_query` -- aqui sobre `inventory_asset` en
    vez de `nm_incident_product`: vigente = sigue `status = 'prestada'` (no
    se ha devuelto -- una `devolucion` la regresaria a `disponible`/
    `en_uso`), `due_date` no nulo y ya pasado contra el momento real
    (`ahora`), NUNCA contra `fecha_fin` -- una pieza vencida hace 3 dias que
    sigue sin devolverse cuenta ese dia cada vez que se recalcula. Se agrupa
    por el DIA de `due_date` que cae en `[fecha_inicio, fecha_fin]`.

    Responsable: `id_holder` -- quien tiene la pieza ahora mismo.

    Sin alcance de proyecto, mismo motivo que
    `material_prestado_por_responsable_query`.
    """
    ahora = datetime.now()
    fecha_col = func.date(InventoryAsset.due_date)
    condiciones = [
        InventoryAsset.deletion_date.is_(None),
        InventoryAsset.status == PRESTADA,
        InventoryAsset.due_date.isnot(None),
        InventoryAsset.due_date < ahora,
        fecha_col >= fecha_inicio,
        fecha_col <= fecha_fin,
    ]

    empleados = (filtros_dimension or {}).get("empleados")
    if empleados:
        condiciones.append(InventoryAsset.id_holder.in_(empleados))

    stmt = (
        select(InventoryAsset.id_holder, fecha_col.label("fecha"), func.count())
        .where(*condiciones)
        .group_by(InventoryAsset.id_holder, fecha_col)
        .order_by(InventoryAsset.id_holder, fecha_col)
    )
    return session.execute(stmt).all()


def lotes_proximos_a_caducar_query(session, fecha_inicio, fecha_fin, filtros_dimension, actor_project):
    """Lotes por producto cuya caducidad (`expiry_date`) cae en el rango, por dia.

    No hay un "umbral de dias" separado aqui a proposito: el propio rango de
    fechas que el usuario ya elige en el widget (`fecha_inicio`/`fecha_fin`)
    ES el umbral -- pedir "hoy a hoy+30" ya es preguntar "que caduca en los
    proximos 30 dias". Se agrupa por el DIA exacto de `expiry_date`, no en un
    solo total, para poder ver picos de vencimiento en el tiempo.

    Dimension "producto" (`id_product`), no "empleado" -- ver
    `DIMENSION_JSON_KEY`.

    Sin alcance de proyecto: un lote es inventario propio de almacen, no de
    un proyecto de cliente (mismo criterio que el resto de los KPIs de
    almacen de este archivo).
    """
    fecha_col = InventoryLot.expiry_date
    condiciones = [
        InventoryLot.deletion_date.is_(None),
        InventoryLot.expiry_date.isnot(None),
        fecha_col >= fecha_inicio,
        fecha_col <= fecha_fin,
    ]

    productos = (filtros_dimension or {}).get("productos")
    if productos:
        condiciones.append(InventoryLot.id_product.in_(productos))

    stmt = (
        select(InventoryLot.id_product, fecha_col.label("fecha"), func.count())
        .where(*condiciones)
        .group_by(InventoryLot.id_product, fecha_col)
        .order_by(InventoryLot.id_product, fecha_col)
    )
    return session.execute(stmt).all()


def articulos_bajo_stock_query(session, fecha_inicio, fecha_fin, filtros_dimension, actor_project):
    """Existencia ACTUAL por producto (`inventory_stock`, sumada entre ubicaciones).

    No es una serie por dia: `inventory_stock` no guarda historia, solo el
    saldo de HOY (ver el docstring de la tabla). Por eso regresa una sola
    fila por producto fechada en `fecha_fin`: es una foto del saldo actual,
    no una reconstruccion historica -- `fecha_inicio` no se usa para nada mas
    que mantener la firma comun de `query_builder`. Como cada noche repite la
    foto completa, se declara `agregacion="ultimo"`: sumar las noches del
    rango multiplicaria la existencia por el numero de dias.

    El KPI guarda la CANTIDAD en existencia, no un si-o-no de "esta bajo
    stock": el umbral para decidir que cuenta como "bajo" se captura en el
    WIDGET (decision explicita de Aurora) -- no hay columna de stock minimo
    en `product`/`material`/`product_sale_config` (se reviso el modelo
    completo), y anadirla obligaria a mantenerla actualizada por producto sin
    que nadie la pida todavia. Comparar el valor contra el umbral es trabajo
    de la pantalla, no de este query.

    Dimension "producto". Sin alcance de proyecto: el saldo de almacen no le
    pertenece a un proyecto de cliente.
    """
    productos = (filtros_dimension or {}).get("productos")
    condiciones = []
    if productos:
        condiciones.append(InventoryStock.id_product.in_(productos))

    stmt = (
        select(InventoryStock.id_product, func.sum(InventoryStock.quantity))
        .where(*condiciones)
        .group_by(InventoryStock.id_product)
        .order_by(InventoryStock.id_product)
    )
    return [(id_product, fecha_fin, cantidad) for id_product, cantidad in session.execute(stmt).all()]


class KpiDefinition:
    def __init__(self, clave, etiqueta, modulo, dimensiones,
                 query_builder, *, direccion, graficas_permitidas, grafica_default,
                 agregacion=None, unidad="numero", alcance_proyecto=True, modo="snapshot"):
        self.clave = clave
        self.etiqueta = etiqueta
        self.modulo = modulo               # clave de MODULOS en app/modules/registry.py
        self.dimensiones = dimensiones      # tupla, ej. ("empleado",)
        self.query_builder = query_builder  # ver firma de ventas_por_empleado_query
        # Si el KPI vive en `kpi_snapshot` con recalculo periodico ("snapshot",
        # el default -- los 16 KPIs de siempre) o si su query_builder se llama
        # EN VIVO al renderizar el widget, sobre datos de detalle que no caben
        # en "un numero por entidad y dia" (ej. cada renglon de un prestamo
        # individual con su fecha exacta) -- ver MODOS arriba.
        self.modo = modo
        # Obligatoria para un KPI "snapshot" (revienta en _validar() si falta,
        # no con TypeError -- antes era un kwarg sin default y Python lo
        # exigia solo; ahora la exigencia es condicional al modo, asi que se
        # valida a mano). Un KPI "vivo" NO debe declararla: no hay nada que
        # combinar entre dias, siempre es "ahora" -- ver AGREGACIONES.
        self.agregacion = agregacion
        self.unidad = unidad
        # Como colorear una variacion (flecha del widget de tipo numero):
        # "alto_es_mejor"/"bajo_es_mejor"/"neutral" -- obligatorio y sin
        # default a proposito, igual que `agregacion`: un KPI sin esta
        # decision explicita de negocio revienta al importar. Ver DIRECCIONES.
        self.direccion = direccion
        # Que tipos de grafica puede mostrar este KPI y cual va preseleccionado
        # -- ver GRAFICAS. Obligatorios y sin default: hoy no los lee ningun
        # endpoint ni el frontend (es metadato puro, preparado para el
        # rediseno del dashboard), pero se exigen desde ya para que ningun KPI
        # nuevo se quede sin esta decision tomada.
        self.graficas_permitidas = graficas_permitidas
        self.grafica_default = grafica_default
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


# Los 16 KPIs de siempre no restringen tipo de grafica -- hoy nada valida
# `graficas_permitidas` en ningun endpoint ni en el frontend, y no hay
# visibilidad de que widgets reales ya existen configurados en cada
# ambiente. Restringir de mas aqui podria invalidar en el futuro (cuando el
# rediseno del dashboard SI empiece a leer este campo) un widget que alguien
# ya configuro con una grafica que aqui se hubiera excluido. Los KPIs NUEVOS
# de esta tarea si declaran un conjunto acotado: no tienen ningun widget real
# configurado todavia en ningun ambiente.
TODAS_LAS_GRAFICAS = GRAFICAS

KPI_REGISTRY = (
    KpiDefinition(
        clave="ventas_por_empleado",
        etiqueta="Ventas por empleado",
        modulo="facturacion",
        dimensiones=("empleado",),
        query_builder=ventas_por_empleado_query,
        agregacion="suma",
        unidad="moneda",
        direccion="alto_es_mejor",
        graficas_permitidas=TODAS_LAS_GRAFICAS,
        grafica_default="barras",
    ),
    KpiDefinition(
        clave="egresos_por_empleado",
        etiqueta="Egresos por empleado",
        modulo="facturacion",
        dimensiones=("empleado",),
        query_builder=egresos_por_empleado_query,
        agregacion="suma",
        unidad="moneda",
        direccion="bajo_es_mejor",
        graficas_permitidas=TODAS_LAS_GRAFICAS,
        grafica_default="barras",
    ),
    KpiDefinition(
        clave="desarrollo_por_empleado",
        etiqueta="Desarrollo por empleado",
        modulo="operaciones",
        dimensiones=("empleado",),
        query_builder=desarrollo_por_empleado_query,
        agregacion="promedio_ponderado",
        unidad="porcentaje",
        direccion="alto_es_mejor",
        graficas_permitidas=TODAS_LAS_GRAFICAS,
        grafica_default="barras",
    ),
    KpiDefinition(
        clave="vales_vencidos_por_responsable",
        etiqueta="Vales vencidos por responsable",
        modulo="operaciones",
        dimensiones=("empleado",),
        query_builder=vales_vencidos_por_responsable_query,
        agregacion="suma",
        unidad="numero",
        alcance_proyecto=False,
        direccion="bajo_es_mejor",
        graficas_permitidas=TODAS_LAS_GRAFICAS,
        grafica_default="tabla",
    ),
    KpiDefinition(
        clave="incidentes_resueltos_por_empleado",
        etiqueta="Incidentes resueltos por empleado",
        modulo="operaciones",
        dimensiones=("empleado",),
        query_builder=incidentes_resueltos_por_empleado_query,
        agregacion="promedio_ponderado",
        unidad="porcentaje",
        alcance_proyecto=False,
        direccion="alto_es_mejor",
        graficas_permitidas=TODAS_LAS_GRAFICAS,
        grafica_default="barras",
    ),
    KpiDefinition(
        clave="cancelaciones_por_empleado",
        etiqueta="Cancelaciones por empleado",
        modulo="operaciones",
        dimensiones=("empleado",),
        query_builder=cancelaciones_por_empleado_query,
        agregacion="suma",
        unidad="numero",
        alcance_proyecto=False,
        direccion="bajo_es_mejor",
        graficas_permitidas=TODAS_LAS_GRAFICAS,
        grafica_default="barras",
    ),
    KpiDefinition(
        clave="ordenes_laboratorio_entregadas_por_tecnico",
        etiqueta="Órdenes de laboratorio entregadas por técnico",
        modulo="laboratorio",
        dimensiones=("empleado",),
        query_builder=ordenes_laboratorio_entregadas_por_tecnico_query,
        agregacion="suma",
        unidad="numero",
        direccion="alto_es_mejor",
        graficas_permitidas=TODAS_LAS_GRAFICAS,
        grafica_default="barras",
    ),
    KpiDefinition(
        clave="tiempo_promedio_reparacion_laboratorio_por_tecnico",
        etiqueta="Tiempo promedio de reparación por técnico",
        modulo="laboratorio",
        dimensiones=("empleado",),
        query_builder=tiempo_promedio_reparacion_laboratorio_por_tecnico_query,
        agregacion="promedio_ponderado",
        unidad="dias",
        direccion="bajo_es_mejor",
        graficas_permitidas=TODAS_LAS_GRAFICAS,
        grafica_default="barras",
    ),
    KpiDefinition(
        clave="costo_promedio_reparacion_laboratorio_por_tecnico",
        etiqueta="Costo promedio de reparación por técnico",
        modulo="laboratorio",
        dimensiones=("empleado",),
        query_builder=costo_promedio_reparacion_laboratorio_por_tecnico_query,
        agregacion="promedio_ponderado",
        unidad="moneda",
        direccion="neutral",
        graficas_permitidas=TODAS_LAS_GRAFICAS,
        grafica_default="barras",
    ),
    KpiDefinition(
        clave="documentos_vencidos_por_responsable",
        etiqueta="Documentos vencidos por responsable",
        modulo="documentos",
        dimensiones=("empleado",),
        query_builder=documentos_vencidos_por_responsable_query,
        agregacion="suma",
        unidad="numero",
        direccion="bajo_es_mejor",
        graficas_permitidas=TODAS_LAS_GRAFICAS,
        grafica_default="tabla",
    ),
    # --- variables/KPIs adicionales (pedido de Aurora: "opcionales,
    # adicionales", para comparar variables como ingresos vs egresos en un
    # mismo grafico y convertir datos sueltos en informacion) -------------
    KpiDefinition(
        clave="ingresos_totales",
        etiqueta="Ingresos totales",
        modulo="facturacion",
        dimensiones=("global",),
        query_builder=ingresos_totales_query,
        agregacion="suma",
        unidad="moneda",
        direccion="alto_es_mejor",
        graficas_permitidas=TODAS_LAS_GRAFICAS,
        grafica_default="linea",
    ),
    KpiDefinition(
        clave="egresos_totales",
        etiqueta="Egresos totales",
        modulo="facturacion",
        dimensiones=("global",),
        query_builder=egresos_totales_query,
        agregacion="suma",
        unidad="moneda",
        direccion="bajo_es_mejor",
        graficas_permitidas=TODAS_LAS_GRAFICAS,
        grafica_default="linea",
    ),
    KpiDefinition(
        clave="material_prestado_por_responsable",
        etiqueta="Material prestado por responsable",
        modulo="inventario",
        dimensiones=("empleado",),
        query_builder=material_prestado_por_responsable_query,
        agregacion="suma",
        unidad="numero",
        alcance_proyecto=False,
        direccion="neutral",
        graficas_permitidas=TODAS_LAS_GRAFICAS,
        grafica_default="barras",
    ),
    KpiDefinition(
        clave="prestamos_vencidos_por_responsable",
        etiqueta="Préstamos de material vencidos por responsable",
        modulo="inventario",
        dimensiones=("empleado",),
        query_builder=prestamos_vencidos_por_responsable_query,
        agregacion="suma",
        unidad="numero",
        alcance_proyecto=False,
        direccion="bajo_es_mejor",
        graficas_permitidas=TODAS_LAS_GRAFICAS,
        grafica_default="tabla",
    ),
    KpiDefinition(
        clave="lotes_proximos_a_caducar",
        etiqueta="Lotes próximos a caducar",
        modulo="inventario",
        dimensiones=("producto",),
        query_builder=lotes_proximos_a_caducar_query,
        agregacion="suma",
        unidad="numero",
        alcance_proyecto=False,
        direccion="bajo_es_mejor",
        graficas_permitidas=TODAS_LAS_GRAFICAS,
        grafica_default="tabla",
    ),
    KpiDefinition(
        clave="articulos_bajo_stock",
        etiqueta="Artículos bajo stock",
        modulo="inventario",
        dimensiones=("producto",),
        query_builder=articulos_bajo_stock_query,
        agregacion="ultimo",
        unidad="numero",
        alcance_proyecto=False,
        direccion="bajo_es_mejor",
        graficas_permitidas=TODAS_LAS_GRAFICAS,
        grafica_default="tabla",
    ),
)


# `id_kpi_definition` en `kpi_snapshot`/las rutas es un entero de BD -- este
# mapa resuelve `alcance_proyecto` a partir de la `clave` de KpiDefinition
# (la fila real de `kpi_definition` trae `clave`, sembrada 1 a 1 desde este
# registro). Lo consumen `app/jobs/tasks_kpis.py` y `app/routes/kpi.py`, ver
# el comentario de `KpiDefinition.alcance_proyecto`.
ALCANCE_PROYECTO_POR_CLAVE = {kpi.clave: kpi.alcance_proyecto for kpi in KPI_REGISTRY}

# Misma idea que el mapa de arriba, pero para la dimension: que tipo de
# entidad desglosa cada KPI ("empleado"/"producto"/"global"). Lo consume
# `app/routes/kpi.py` para saber que llave de `dimension_key` leer al sumar
# (via `DIMENSION_JSON_KEY`) sin tener que resembrar la logica de dimensiones
# fuera de este registro.
DIMENSION_POR_CLAVE = {kpi.clave: kpi.dimensiones[0] for kpi in KPI_REGISTRY}

# Y para la regla de agregacion (ver AGREGACIONES): la consume `_totales()` en
# `app/routes/kpi.py` para saber como combinar los snapshots del rango.
AGREGACION_POR_CLAVE = {kpi.clave: kpi.agregacion for kpi in KPI_REGISTRY}


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
        if kpi.modo not in MODOS:
            raise RuntimeError(
                f"El KPI '{kpi.clave}' declara el modo desconocido '{kpi.modo}' "
                f"(validos: {', '.join(MODOS)})."
            )
        if kpi.modo == "snapshot" and kpi.agregacion is None:
            raise RuntimeError(
                f"El KPI '{kpi.clave}' es de modo 'snapshot' y necesita declarar 'agregacion' "
                f"(validas: {', '.join(AGREGACIONES)})."
            )
        if kpi.modo == "vivo" and kpi.agregacion is not None:
            raise RuntimeError(
                f"El KPI '{kpi.clave}' es de modo 'vivo': no participa del job ni del backfill, "
                "no debe declarar 'agregacion'."
            )
        if kpi.agregacion is not None and kpi.agregacion not in AGREGACIONES:
            raise RuntimeError(
                f"El KPI '{kpi.clave}' declara la agregacion desconocida '{kpi.agregacion}' "
                f"(validas: {', '.join(AGREGACIONES)})."
            )
        if kpi.direccion not in DIRECCIONES:
            raise RuntimeError(
                f"El KPI '{kpi.clave}' declara la direccion desconocida '{kpi.direccion}' "
                f"(validas: {', '.join(DIRECCIONES)})."
            )
        if kpi.unidad not in UNIDADES:
            raise RuntimeError(
                f"El KPI '{kpi.clave}' declara la unidad desconocida '{kpi.unidad}' "
                f"(validas: {', '.join(UNIDADES)})."
            )
        for dimension in kpi.dimensiones:
            if dimension not in DIMENSIONES:
                raise RuntimeError(
                    f"El KPI '{kpi.clave}' declara la dimension desconocida '{dimension}' "
                    f"(validas: {', '.join(DIMENSIONES)})."
                )
        if not kpi.graficas_permitidas:
            raise RuntimeError(f"El KPI '{kpi.clave}' no declara ninguna grafica permitida.")
        for grafica in kpi.graficas_permitidas:
            if grafica not in GRAFICAS:
                raise RuntimeError(
                    f"El KPI '{kpi.clave}' declara la grafica desconocida '{grafica}' "
                    f"(validas: {', '.join(GRAFICAS)})."
                )
        if kpi.grafica_default not in kpi.graficas_permitidas:
            raise RuntimeError(
                f"El KPI '{kpi.clave}' declara grafica_default='{kpi.grafica_default}' "
                "que no esta en su propia lista de graficas_permitidas."
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
