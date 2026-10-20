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
import unicodedata
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import Date, Integer, String, and_, case, cast, func, literal, or_, select, text, type_coerce

from app.models.document import Document
from app.models.incident import Incident
from app.models.incident_type import IncidentType
from app.models.inventory_asset import InventoryAsset, PRESTADA
from app.models.inventory_asset_event import InventoryAssetEvent, PRESTAMO
from app.models.inventory_lot import InventoryLot
from app.models.inventory_status import InventoryStatus
from app.models.inventory_stock import InventoryStock
from app.models.invoice import Invoice
from app.models.laboratory import LaboratoryServiceOrder
from app.models.nm_incident_product import NmIncidentProduct
from app.models.product import Product
from app.models.task import Task
from app.models.user import User
from app.services.warehouse_voucher_service import (
    CIERRE_SENTINELA, SALIDA, TIPOS_DE_BAJA, _estado_del_renglon, _vales_de_baja,
)
from app.modules.registry import MODULO_POR_CLAVE
from app.kpis.dimensiones import CATALOGO as CATALOGO_DE_DIMENSIONES, DIMENSION_POR_CLAVE as CATALOGO_POR_CLAVE

# Que llave de `dimension_key` (JSONB, en `kpi_snapshot`) le corresponde a cada
# tipo de dimension declarado en `KpiDefinition.dimensiones`. "global" no
# agrega ninguna llave de entidad -- el KPI no se desglosa por nada, solo
# guarda `id_proyect` cuando aplica (ver `alcance_proyecto`). La consumen
# `app/jobs/tasks_kpis.py` (para saber que llave escribir al insertar el
# snapshot) y `app/routes/kpi.py` (para saber que llave leer al sumar).
#
# Ya no se escribe a mano: se DERIVA del catalogo de `app/kpis/dimensiones.py`,
# donde cada dimension (empleado, producto, familia, mesero, platillo, mesa,
# cliente, unidad, operador...) se declara una sola vez con su llave, su
# etiqueta, su tipo y quien resuelve los nombres. Para "estado" el valor de cada
# fila no es un id sino el nombre de una categoria fija ("abierta"/"cerrada",
# "Entrada"/"Salida"/...); `_totales()` en routes/kpi.py ya es generico sobre el
# TIPO del valor porque siempre lo compara como texto (`.astext`).
DIMENSION_JSON_KEY = {d.clave: d.json_key for d in CATALOGO_DE_DIMENSIONES}

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
UNIDADES = ("numero", "porcentaje", "moneda", "dias", "piezas", "minutos")

# Vocabulario cerrado de dimensiones: las claves del catalogo de
# `app/kpis/dimensiones.py` (las cinco de siempre, en su orden, y despues las de
# restaurante y logistica).
DIMENSIONES = tuple(d.clave for d in CATALOGO_DE_DIMENSIONES)

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
        # Una baja (destruccion, extravio) no se reclama: mismo criterio que
        # `warehouse_voucher_service.vales_vencidos()`. Ver TIPOS_DE_BAJA.
        NmIncidentProduct.id_incident.notin_(_vales_de_baja()),
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
    * Rango de fechas: `Incident.incident_date`, YA NO `creation_date` (cambio
      de esta tarea). `creation_date` declara `nullable=False,
      server_default=func.now()` en el modelo, pero la tabla real en Postgres
      no tiene ese default (confirmado en `init.sql`: `"creation_date"
      TIMESTAMP NULL`, sin `DEFAULT`) -- solo queda poblado cuando algo lo
      asigna a mano. `IncidentService.create()` SI lo hace (hereda
      `_fill_system_defaults()` de `CrudService`, pensado justo para
      compensar que `init.sql` no trae el default -- ver su propio
      comentario), asi que un incidente capturado normal por la app SI trae
      `creation_date`. Pero `migrate_adser.py::migrar_incident` inserta
      directo con `session.add(Incident(...))`, sin pasar por ese servicio:
      los 139 incidentes migrados de Adser quedan con `creation_date` NULL, y
      `func.date(NULL) >= fecha_inicio` nunca es verdadero -- quedaban
      invisibles en cualquier rango, para cualquier cliente con datos
      migrados de un sistema legado.
      Contrapartida real de este cambio, para que quede documentada: un
      incidente capturado normal SIN `incident_date` (el propio
      `incident_service._validate_dates` lo permite en NULL) ahora SI queda
      fuera de este KPI, cosa que antes no pasaba (via `creation_date`, que
      la captura normal siempre llena). Se acepta el cambio tal cual lo pide
      la tarea -- mismo campo que ya usan los KPIs nuevos de este archivo --
      sin agregar un `COALESCE` a `creation_date` como respaldo, que es una
      decision de producto aparte, no de esta tarea.
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
    * Una fila por `id_user` y por DIA de `incident_date`, con el numero de
      incidentes de ese dia como `peso` -- mismo motivo que
      `desarrollo_por_empleado_query` (`promedio_ponderado`).
    """
    fecha_col = func.date(Incident.incident_date)
    condiciones = [
        Incident.deletion_date.is_(None),
        Incident.incident_date.isnot(None),
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


def incidencias_abiertas_por_empleado_query(session, fecha_inicio, fecha_fin, filtros_dimension, actor_project):
    """Incidencias/vales ABIERTOS (creados), por responsable y por dia.

    * Vigencia: `Incident.deletion_date IS NULL`. Sin filtro de estatus a
      proposito: cuenta cualquier incidencia que se haya abierto, sin
      importar en que quedo -- "cuantas abre cada quien", no "cuantas
      resuelve" (eso ya lo mide `incidentes_resueltos_por_empleado_query`).
    * Responsable: `Incident.id_user` -- el usuario a cuyo nombre esta el vale,
      es decir quien TIENE el material, no necesariamente quien lo capturo. Es
      el mismo campo que ya usa `vales_vencidos_por_responsable_query`. NO
      `created_by`: ese es solo auditoria (entero plano sin FK, no editable
      en el formulario) y puede diferir de quien realmente tiene el material.
    * Fecha: `Incident.incident_date`, DELIBERADAMENTE no `creation_date`.
      El modelo declara `creation_date` como `nullable=False,
      server_default=func.now()`, pero la tabla real en Postgres NO tiene
      ese default (verificado con el describe de psql sobre la tabla real: columna nullable, sin
      `Default`) -- discrepancia real entre el modelo y el esquema, ajena a
      esta tarea, no introducida aqui. Como ni `migrate_adser.py::migrar_incident`
      ni el alta normal de un incidente (`incident_service.py`) asignan
      `creation_date` a mano, confiando en ese default que no existe,
      `creation_date` queda **NULL** -- no "fijo en la fecha de la
      migracion" como se penso al principio de esta tarea, sino ausente del
      todo, para incidentes migrados Y para incidentes nuevos por igual. Eso
      ya afecta hoy a `incidentes_resueltos_por_empleado_query`, que agrupa
      por `func.date(Incident.creation_date)`: con esa columna en NULL,
      `func.date(NULL) >= fecha_inicio` nunca es verdadero, asi que CUALQUIER
      incidente (no solo los migrados de Adser) queda invisible para ese KPI
      en cualquier rango -- fuera de alcance de esta tarea, no se toca aqui,
      pero vale la pena confirmarlo con el equipo. Este KPI nuevo lo evita
      desde el diseno usando `incident_date`, el campo que `migrar_incident`
      SI llena con la fecha real (`fecha_incidente` de origen) y que el alta
      normal tambien captura como dato de negocio real, no como auditoria.
    * Sin alcance de proyecto: un vale de almacen es un `Incident` con
      `id_proyect` NULL, mismo motivo que `vales_vencidos_por_responsable_query`.
    """
    fecha_col = func.date(Incident.incident_date)
    condiciones = [
        Incident.deletion_date.is_(None),
        Incident.incident_date.isnot(None),
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


def incidencias_pendientes_query(session, fecha_inicio, fecha_fin, filtros_dimension, actor_project):
    """Foto: cuantas incidencias seguian sin cerrar en cada dia del rango.

    Para una fecha D, "pendiente en D" es una incidencia creada hasta D
    (`incident_date <= D`) que NO estaba cerrada en D -- no necesariamente
    sin cerrar HOY: pudo cerrarse despues de D. "Sin cerrar en D" es
    `close_date IS NULL` (nunca se cerro), `close_date == CIERRE_SENTINELA`
    (el sentinel heredado de Adser -- ver `_sin_cerrar` en
    warehouse_voucher_service.py, que compara exactamente contra estos dos
    casos) o `close_date > D` (se cerro, pero DESPUES de la fecha que se esta
    reconstruyendo; cerrarse justo EN D ya no cuenta como pendiente ese dia).

    Esto permite reconstruir el valor de cualquier fecha PASADA de forma
    exacta -- necesario porque este KPI es una foto por dia, no un evento que
    ya traiga su propia fecha en una columna: cada dia del rango es una
    pregunta independiente sobre el estado del universo completo de
    incidencias en ese momento, no algo que un GROUP BY normal resuelva.

    Se genera la serie de dias del rango con `generate_series` (Postgres,
    igual que el resto de este archivo asume ese motor) y se hace LEFT JOIN
    contra `Incident` -- OUTER, no INNER: un dia sin ninguna incidencia
    pendiente debe regresar 0, no faltar de la respuesta. Una fila ausente en
    `kpi_snapshot` se lee como "no calculado", no como "cero" (ver el
    diagnostico de esta tarea) -- y como este KPI es `agregacion="ultimo"`,
    `_totales()` en routes/kpi.py toma el snapshot del ULTIMO dia con fila;
    si faltara el ultimo dia real del rango por no tener incidencias
    pendientes, tomaria el dia anterior por error.

    Dimension "global" (una sola foto, sin desglose por empleado/producto).
    Sin alcance de proyecto, mismo motivo que el resto de los KPIs sobre
    `Incident` de este archivo.
    """
    dias = (
        select(cast(func.generate_series(fecha_inicio, fecha_fin, text("interval '1 day'")), Date).label("dia"))
        .subquery()
    )
    condicion_pendiente = and_(
        Incident.deletion_date.is_(None),
        Incident.incident_date.isnot(None),
        func.date(Incident.incident_date) <= dias.c.dia,
        or_(
            Incident.close_date.is_(None),
            Incident.close_date == CIERRE_SENTINELA,
            func.date(Incident.close_date) > dias.c.dia,
        ),
    )
    stmt = (
        select(dias.c.dia, func.count(Incident.id_incident))
        .select_from(dias)
        .outerjoin(Incident, condicion_pendiente)
        .group_by(dias.c.dia)
        .order_by(dias.c.dia)
    )
    return [(None, dia, valor) for dia, valor in session.execute(stmt).all()]


# Las 4 categorias fijas de `prestamos_abiertos_por_antiguedad`, en el orden en que se leen
# (de menos a mas antiguo). Son `estado` de la dimension: texto, no ids.
ANTIGUEDAD_CATEGORIAS = ("0-30", "31-60", "61-90", "+90")
# Verde -> ambar -> naranja -> rojo: a mas dias prestado, mas urgente.
ANTIGUEDAD_COLORES = {"0-30": "#22b573", "31-60": "#f0a93b", "61-90": "#f58a3c", "+90": "#e5484d"}


def prestamos_abiertos_por_antiguedad_query(session, fecha_inicio, fecha_fin, filtros_dimension, actor_project):
    """Foto: renglones de vale prestados sin devolver, por antiguedad, en cada dia del rango.

    Mismo universo que `material_prestado_actual_query` (el KPI "vivo" que lista estos
    mismos renglones): direccion "Salida", sin vales de BAJA (`TIPOS_DE_BAJA`:
    destruccion y extravio; "Dañado" SI cuenta), con `Incident.incident_date`, sin
    borrados. Aqui se cuentan por antiguedad en vez de listarse.

    Antiguedad en un dia D = `D - incident_date` (la misma "dias prestado" de la tabla,
    que usa D = hoy), en 4 categorias fijas: "0-30", "31-60", "61-90" y "+90" dias.

    Reconstruccion de cualquier dia pasado, igual que `incidencias_pendientes_query`: un
    renglon estaba abierto en D si su vale ya existia (`incident_date <= D`) y NO estaba
    cerrado en D: `close_date` nulo, el sentinel heredado de Adser (`CIERRE_SENTINELA`,
    que no es un cierre real) o posterior a D (cerrarse EN D ya no cuenta ese dia). Asi la
    foto de un dia anterior sale exacta, con la antiguedad que tenia ENTONCES.

    Siempre regresa las 4 categorias de cada dia, con 0 cuando no hay renglones: el
    agregado "ultimo" toma el ultimo dia con filas, y una categoria ausente se lee como
    "no calculada", no como cero.

    Dimension "estado" (categoria fija). Sin alcance de proyecto, mismo motivo que el resto
    de los KPIs sobre `Incident` de este archivo. La unidad es renglones de vale.
    """
    dias = (
        select(cast(func.generate_series(fecha_inicio, fecha_fin, text("interval '1 day'")), Date).label("dia"))
        .subquery()
    )
    antiguedad = dias.c.dia - func.date(Incident.incident_date)
    categoria = case(
        (antiguedad <= 30, ANTIGUEDAD_CATEGORIAS[0]),
        (antiguedad <= 60, ANTIGUEDAD_CATEGORIAS[1]),
        (antiguedad <= 90, ANTIGUEDAD_CATEGORIAS[2]),
        else_=ANTIGUEDAD_CATEGORIAS[3],
    )
    stmt = (
        select(categoria.label("categoria"), dias.c.dia, func.count())
        .select_from(dias)
        .join(
            Incident,
            and_(
                Incident.deletion_date.is_(None),
                Incident.incident_date.isnot(None),
                func.date(Incident.incident_date) <= dias.c.dia,
            ),
        )
        .join(
            NmIncidentProduct,
            and_(
                NmIncidentProduct.id_incident == Incident.id_incident,
                NmIncidentProduct.deletion_date.is_(None),
                NmIncidentProduct.direction == SALIDA,
                or_(
                    NmIncidentProduct.close_date.is_(None),
                    NmIncidentProduct.close_date == CIERRE_SENTINELA,
                    func.date(NmIncidentProduct.close_date) > dias.c.dia,
                ),
            ),
        )
        .outerjoin(IncidentType, IncidentType.id_incident_type == Incident.id_incident_type)
        .where(
            or_(
                IncidentType.incident_type_description.is_(None),
                func.lower(func.trim(IncidentType.incident_type_description)).notin_(TIPOS_DE_BAJA),
            )
        )
        .group_by(categoria, dias.c.dia)
    )
    conteos = {(dia, cat): cantidad for cat, dia, cantidad in session.execute(stmt).all()}
    filas = []
    dia = fecha_inicio
    while dia <= fecha_fin:
        for cat in ANTIGUEDAD_CATEGORIAS:
            filas.append((cat, dia, conteos.get((dia, cat), 0)))
        dia += timedelta(days=1)
    return filas


# Las 6 categorias fijas de `piezas_por_estado`, en el orden en que se leen: de lo normal a lo grave.
# Son `estado` de la dimension: texto, no ids. Los nombres son los de `material_por_estado`
# ("Destruccion" sin acento, "Dañado" con ñ) para que los dos KPIs se lean igual.
PIEZAS_CATEGORIAS = ("Entrada", "Salida", "En reparación", "Dañado", "Extraviado", "Destruccion")
# Paleta de `material_por_estado`, mas violeta para "En reparación" (una pieza en el taller no esta
# ni prestada ni perdida: no debe leerse como Salida, que es azul).
PIEZAS_COLORES = {
    "Entrada": "#22b573",
    "Salida": "#2f8fe0",
    "En reparación": "#8b6fe0",
    "Dañado": "#f0a93b",
    "Extraviado": "#ef6f5c",
    "Destruccion": "#e0559b",
}
# Estado de catalogo (`inventory_status.inventory_status_code`, el que ya traen los productos) ->
# categoria. Los demas codigos (`activo`, `disponible`...) no son un problema de la pieza: caen en
# Salida/Entrada segun tenga o no un prestamo abierto.
PIEZAS_CATEGORIA_POR_ESTADO = {
    "retirado": "Destruccion",
    "extraviado": "Extraviado",
    "danado": "Dañado",
    "en_reparacion": "En reparación",
}


def piezas_por_estado_query(session, fecha_inicio, fecha_fin, filtros_dimension, actor_project):
    """Foto de HOY: cuantas piezas hay en cada estado. PENDIENTE DE CONCILIAR contra tyakxa-dev.

    PENDIENTE DE CONCILIAR contra tyakxa-dev (`id_inventory_status` real) antes de mostrarlo a
    Adser: el CSV de estado de piezas de Alan (docs/despliegues/2026-09-30_estado_de_piezas_adser.csv)
    trae el texto ANTIGUO del estado, no `id_inventory_status`, asi que solo valida la derivacion
    "por analogia". Falta correr `backend/scripts/conciliar_piezas_por_estado.sql` ahi. Ver
    docs/despliegues/2026-10-01_piezas_por_estado.md. Mientras tanto no esta en el perfil de
    permisos ni en la plantilla del tablero de Adser.

    Se cuentan PIEZAS = filas de `product` con `deletion_date IS NULL` (en Adser cada fila es una
    herramienta fisica), no `SUM(quantity)` ni renglones de vale. Cada pieza cae en UNA categoria,
    la primera que cumpla, en este orden:

        Destruccion > Extraviado > Dañado > En reparación > Salida > Entrada

    * Las cuatro primeras salen de `product.id_inventory_status` (`PIEZAS_CATEGORIA_POR_ESTADO`).
    * Salida: la pieza tiene al menos UN renglon de vale abierto, de direccion Salida y de un vale
      que no sea de baja. Mismo universo que `prestamos_abiertos_por_antiguedad` (abierto =
      `close_date` nulo o el centinela de Adser, `CIERRE_SENTINELA`; sin borrados; vale con
      `incident_date`; sin `TIPOS_DE_BAJA`). Dos renglones abiertos de la misma pieza cuentan UNA vez.
      Una pieza Dañada que ademas esta prestada se cuenta como Dañado (gana el estado).
    * Entrada: todo lo demas.
    * Incluye todo `product`: `stock_purpose` no separa herramientas de consumibles (en Adser todo es
      `uso_interno`).
    * Las piezas serializadas (`inventory_asset.status`) quedan fuera, como en el resto de los KPIs.

    El estado de catalogo no guarda historia: es una FOTO fechada en `fecha_fin` (agregacion
    "ultimo"), no se reconstruyen dias pasados. Siempre regresa las 6 categorias, con 0 cuando no
    hay piezas (una categoria ausente se leeria como "no calculada"). La suma de las 6 es el total
    de piezas. Dimension "estado", sin alcance de proyecto.
    """
    prestada = (
        select(NmIncidentProduct.id_product)
        .join(Incident, Incident.id_incident == NmIncidentProduct.id_incident)
        .outerjoin(IncidentType, IncidentType.id_incident_type == Incident.id_incident_type)
        .where(
            NmIncidentProduct.id_product == Product.id_product,
            NmIncidentProduct.deletion_date.is_(None),
            NmIncidentProduct.direction == SALIDA,
            or_(NmIncidentProduct.close_date.is_(None), NmIncidentProduct.close_date == CIERRE_SENTINELA),
            Incident.deletion_date.is_(None),
            Incident.incident_date.isnot(None),
            or_(
                IncidentType.incident_type_description.is_(None),
                func.lower(func.trim(IncidentType.incident_type_description)).notin_(TIPOS_DE_BAJA),
            ),
        )
        .exists()
    )
    codigo = func.lower(func.trim(InventoryStatus.inventory_status_code))
    categoria = case(
        *[(codigo == estado, nombre) for estado, nombre in PIEZAS_CATEGORIA_POR_ESTADO.items()],
        (prestada, "Salida"),
        else_="Entrada",
    )
    stmt = (
        select(categoria.label("categoria"), func.count())
        .select_from(Product)
        .outerjoin(InventoryStatus, InventoryStatus.id_inventory_status == Product.id_inventory_status)
        .where(Product.deletion_date.is_(None))
        .group_by(categoria)
    )
    conteos = {cat: cantidad for cat, cantidad in session.execute(stmt).all()}
    return [(cat, fecha_fin, conteos.get(cat, 0)) for cat in PIEZAS_CATEGORIAS]


# Que vales cuentan como una PERDIDA de herramienta en `perdidas_por_familia`: destruccion, extravio
# y dañado, por la descripcion del tipo SIN acentos ni mayusculas (el catalogo real trae
# "Destruccion" y "Dañado"; con `translate` tambien valen "Destrucción" y "Danado"). Reparacion NO:
# una herramienta en reparacion no esta perdida.
TIPOS_DE_PERDIDA = ("destruccion", "extraviado", "danado")
# `product.id_familia` nulo se agrupa bajo este valor ("Sin familia"), para que su perdida no
# desaparezca de la grafica.
FAMILIA_SIN_ASIGNAR = 0


def perdidas_por_familia_query(session, fecha_inicio, fecha_fin, filtros_dimension, actor_project):
    """Piezas perdidas por familia de producto y por dia: destruccion + extravio + dañado.

    Flujo (agregacion "suma"): cada renglon de vale cuenta el dia de su `Incident.incident_date`
    (la fecha real del vale, ver `material_por_estado_query`).

    * Se cuentan PIEZAS (`SUM(NmIncidentProduct.quantity)`), no renglones: lo que importa de una
      perdida es cuantas piezas se fueron, y un renglon de 5 piezas dañadas no es lo mismo que
      uno de 1. Es tambien lo que cuenta el Resumen de almacen del sistema anterior.
    * Tipos: `TIPOS_DE_PERDIDA`, sin importar la direccion del renglon (lo define el tipo del vale).
    * Familia: `product.id_familia` (la del PRODUCTO, la columna "Familia" del sistema anterior), no
      la del material. Sin familia -> `FAMILIA_SIN_ASIGNAR`. Los nombres no se guardan aqui: la
      dimension lleva el id y `GET /kpi_snapshot/query` los resuelve al consultar.
    * El top 10 NO se corta aqui: se guarda toda familia con perdidas y el corte se hace al sumar
      el rango (`limite_categorias`).
    * Sin alcance de proyecto, mismo motivo que el resto de los KPIs sobre `Incident`.
    """
    fecha_col = func.date(Incident.incident_date)
    familia = func.coalesce(Product.id_familia, FAMILIA_SIN_ASIGNAR)
    tipo_normalizado = func.translate(func.lower(func.trim(IncidentType.incident_type_description)), "ñáéíóú", "naeiou")
    stmt = (
        select(familia, fecha_col.label("fecha"), func.sum(NmIncidentProduct.quantity))
        .select_from(NmIncidentProduct)
        .join(Incident, Incident.id_incident == NmIncidentProduct.id_incident)
        .join(IncidentType, IncidentType.id_incident_type == Incident.id_incident_type)
        .join(Product, Product.id_product == NmIncidentProduct.id_product)
        .where(
            NmIncidentProduct.deletion_date.is_(None),
            Incident.deletion_date.is_(None),
            Incident.incident_date.isnot(None),
            fecha_col >= fecha_inicio,
            fecha_col <= fecha_fin,
            tipo_normalizado.in_(TIPOS_DE_PERDIDA),
        )
        .group_by(familia, fecha_col)
        .order_by(fecha_col, familia)
    )
    return [(id_familia, fecha, int(piezas)) for id_familia, fecha, piezas in session.execute(stmt).all()]


def incidencias_abiertas_vs_cerradas_query(session, fecha_inicio, fecha_fin, filtros_dimension, actor_project):
    """Incidencias abiertas y cerradas, por dia -- flujo, no foto.

    Dos series bajo la dimension nueva "estado" (valores "abierta"/"cerrada";
    no confundir con `Incident.incident_status`, que trae valores de negocio
    como "resuelta"/"cancelada"): "abierta" cuenta incidencias CREADAS ese
    dia (`incident_date`); "cerrada" cuenta las que se CERRARON ese dia
    (`close_date`), excluyendo el sentinel heredado de Adser
    (`CIERRE_SENTINELA` no es un cierre real -- sin este filtro, cada
    incidencia migrada que sigue abierta se contaria como "cerrada el
    1990-01-01").

    Companero de `incidencias_pendientes_query` (la foto): ese responde
    "cuantas siguen sin cerrar a la fecha", este "cuantas se abrieron/
    cerraron ESE dia". Son agregaciones distintas (ultimo vs suma) sobre
    preguntas distintas -- por eso son dos KPIs separados, no uno con un
    selector de "foto/flujo": el registro solo permite declarar una
    `agregacion` por KPI (ver AGREGACIONES).

    Mismo motivo que el resto de los KPIs de este archivo para usar
    `incident_date` en vez de `creation_date`, y para `alcance_proyecto=False`.
    """
    fecha_apertura = func.date(Incident.incident_date)
    abiertas_stmt = (
        select(literal("abierta").label("estado"), fecha_apertura.label("fecha"), func.count())
        .where(
            Incident.deletion_date.is_(None),
            Incident.incident_date.isnot(None),
            fecha_apertura >= fecha_inicio,
            fecha_apertura <= fecha_fin,
        )
        .group_by(fecha_apertura)
    )
    fecha_cierre = func.date(Incident.close_date)
    cerradas_stmt = (
        select(literal("cerrada").label("estado"), fecha_cierre.label("fecha"), func.count())
        .where(
            Incident.deletion_date.is_(None),
            Incident.close_date.isnot(None),
            Incident.close_date != CIERRE_SENTINELA,
            fecha_cierre >= fecha_inicio,
            fecha_cierre <= fecha_fin,
        )
        .group_by(fecha_cierre)
    )
    filas = list(session.execute(abiertas_stmt).all()) + list(session.execute(cerradas_stmt).all())
    return sorted(filas, key=lambda fila: (fila[1], fila[0]))


def material_por_estado_query(session, fecha_inicio, fecha_fin, filtros_dimension, actor_project):
    """Renglones de vale (`NmIncidentProduct`) por categoria de movimiento, por dia.

    Categoria: `_estado_del_renglon(direction, tipo_descripcion)`
    (warehouse_voucher_service.py) -- la MISMA funcion que ya usan los 4
    reportes reales de vales, no se reinventa el criterio. Devuelve
    "Entrada"/"Salida" segun `direction`, o el texto del tipo de incidencia
    ("Destruccion"/"Dañado"/"Extraviado") cuando el vale es de ese tipo
    especial, sin importar la direccion. Se extendio esa funcion para
    reconocer tambien "extraviado" (antes solo "destruccion"/"dañado") --
    pedido explicito para este KPI, ver el diff de `_estado_del_renglon`.

    Como varias combinaciones distintas de (direction, tipo_descripcion)
    pueden mapear a la MISMA categoria en el mismo dia (ej. dos tipos de
    incidencia distintos, ninguno especial, ambos caen en "Salida"), la
    agregacion por categoria se hace en PYTHON, despues de traer los conteos
    crudos agrupados por los campos reales -- agrupar directo por categoria
    en SQL no es posible porque `_estado_del_renglon` es logica de Python, y
    dejar que dos filas con la misma categoria y fecha lleguen sueltas a
    `tasks_kpis.py` haria que el upsert de la segunda PISE el valor de la
    primera en vez de sumarse (la llave unica de `kpi_snapshot` es
    (kpi, dimension_key, periodo), no hay forma de que dos filas con la
    misma categoria y fecha coexistan).

    Dimension nueva "estado": el valor de cada fila es el nombre de la
    categoria (string), no un id de entidad -- ver `DIMENSION_JSON_KEY`.

    Fecha: `Incident.incident_date` (fecha real del vale), no
    `NmIncidentProduct.creation_date` -- mismo motivo que
    `incidencias_abiertas_por_empleado_query`: la tabla real tampoco tiene
    default para esa columna (mismo hallazgo, verificado con el describe de
    psql sobre la tabla real), y ni `migrar_nm_incident_product` ni el alta
    normal de un renglon la asignan a mano, asi que queda NULL, no "en la
    fecha de la migracion".

    Sin alcance de proyecto, mismo motivo que
    `vales_vencidos_por_responsable_query`.
    """
    fecha_col = func.date(Incident.incident_date)
    condiciones = [
        NmIncidentProduct.deletion_date.is_(None),
        Incident.deletion_date.is_(None),
        Incident.incident_date.isnot(None),
        fecha_col >= fecha_inicio,
        fecha_col <= fecha_fin,
    ]

    stmt = (
        select(NmIncidentProduct.direction, IncidentType.incident_type_description,
               fecha_col.label("fecha"), func.count())
        .select_from(NmIncidentProduct)
        .join(Incident, Incident.id_incident == NmIncidentProduct.id_incident)
        .outerjoin(IncidentType, IncidentType.id_incident_type == Incident.id_incident_type)
        .where(*condiciones)
        .group_by(NmIncidentProduct.direction, IncidentType.incident_type_description, fecha_col)
    )

    acumulado = {}
    for direction, tipo_descripcion, fecha, cantidad in session.execute(stmt).all():
        categoria = _estado_del_renglon(direction, tipo_descripcion)
        llave = (categoria, fecha)
        acumulado[llave] = acumulado.get(llave, 0) + cantidad
    return [
        (categoria, fecha, cantidad)
        for (categoria, fecha), cantidad in sorted(acumulado.items(), key=lambda item: (item[0][1], item[0][0]))
    ]


# Que tipos de vale NO cuentan como "prestado ahora": los de BAJA
# (`TIPOS_DE_BAJA` en warehouse_voucher_service.py: destruccion y extravio), donde
# la herramienta ya no esta con nadie. Es la MISMA regla que usa "Quien tiene que"
# en la app, para que la pantalla y este KPI no se contradigan.
#
# Antes este KPI excluia tambien "Dañado", como estado terminal. Se cambio el
# 2026-09-29 por decision de Alan: no se sabe si quien lo daño todavia lo tiene, y
# es mejor verlo de mas que esconderlo. Los reportes por estado
# (`_estado_del_renglon`) siguen etiquetando los tres.
#
# El filtro va en SQL, no en Python fila por fila, porque este query SI necesita
# LIMIT/OFFSET a nivel SQL (es "vivo", paginado): filtrar DESPUES de traer una
# pagina romperia la paginacion (una pagina podria perder filas reales).


# CONTRATO con el frontend: los campos de cada renglon que devuelve
# `material_prestado_actual_query` (y, por lo tanto, `GET /kpi_definition/<id>/vivo`).
# El Dashboard los lee por nombre (frontend/src/kpi/kpiAdaptadores.js,
# filasTablaPrestamo) y su prueba de contrato usa una respuesta REAL guardada en
# frontend/src/kpi/fixtures/material_prestado_actual.real.json. Un renglon con otro
# nombre de campo no revienta nada: la tabla se pinta VACIA. Por eso esta lista esta
# fijada por una prueba (test_kpi_material_prestado_actual.py) y no debe cambiar sin
# cambiar tambien el adaptador y ese archivo.
CAMPOS_RENGLON_PRESTADO_ACTUAL = (
    "articulo", "dias_prestado", "fecha_prestamo", "id_nm_incident_product", "id_user", "responsable",
)


# Columnas por las que se puede ordenar la tabla de "Material prestado ahora" (el servidor ordena, no el
# navegador: con paginacion, ordenar solo la pagina cargada mentiria).
PRESTADO_ORDENES = ("dias_prestado", "articulo", "responsable", "fecha_prestamo")

# `translate` y no `unaccent`: no hace falta la extension, y `lower()` de Postgres no baja las mayusculas
# con acento en una base de locale "C". Mismo resultado que `sinAcentos` de frontend/src/kpi/kpiPrestamos.js.
_CON_ACENTO = "áàäâéèëêíìïîóòöôúùüûñÁÀÄÂÉÈËÊÍÌÏÎÓÒÖÔÚÙÜÛÑ"
_SIN_ACENTO = "aaaaeeeeiiiioooouuuunaaaaeeeeiiiioooouuuun"


def _sin_acentos(texto) -> str:
    descompuesto = unicodedata.normalize("NFD", str(texto or ""))
    return "".join(c for c in descompuesto if not unicodedata.combining(c)).lower()


def _expresiones_de_prestamo(hoy):
    """Las columnas que ve (y busca) quien mira la tabla, como expresiones SQL.

    El articulo es el mismo que arma el renglon: descripcion, o el codigo, o "Producto #id".
    """
    articulo = func.coalesce(
        func.nullif(Product.descripcion, ""),
        func.nullif(Product.product_code, ""),
        literal("Producto #", String) + cast(NmIncidentProduct.id_nm_incident_product, String),
    )
    fecha = func.to_char(Incident.incident_date, "YYYY-MM-DD")
    dias = type_coerce(literal(hoy, Date) - cast(Incident.incident_date, Date), Integer)
    return articulo, fecha, dias


def _condiciones_de_prestamo(hoy, *, id_user=None, id_user_ambito=None, q=None):
    """Que renglones cuentan como "prestados", mas los filtros de la tabla -- todo en SQL.

    * `id_user_ambito`: el filtro que llega de OTRA tarjeta (clic en una barra). Acota filas y conteos.
    * `id_user`: el desplegable "Responsable". Acota las filas, no los conteos del desplegable.
    * `q`: la busqueda; todas las palabras tienen que aparecer, sin acentos ni mayusculas, en el articulo,
      el responsable, la fecha del vale o los dias.

    Se filtra por `id_user` (el usuario), NO por el nombre: dos personas con el mismo nombre, o un nombre
    sucio repetido en el dato (ej. "ESTANCIA EN EL TALLER"), ya no mezclan sus renglones. Ojo: esto solo
    evita la confusion, NO limpia el dato -- los nombres sucios siguen apareciendo tal cual hasta que se
    limpien en origen.
    """
    condiciones = [
        NmIncidentProduct.deletion_date.is_(None),
        Incident.deletion_date.is_(None),
        Incident.incident_date.isnot(None),
        NmIncidentProduct.direction == SALIDA,
        or_(
            NmIncidentProduct.close_date.is_(None),
            NmIncidentProduct.close_date == CIERRE_SENTINELA,
        ),
        or_(
            IncidentType.incident_type_description.is_(None),
            func.lower(func.trim(IncidentType.incident_type_description)).notin_(TIPOS_DE_BAJA),
        ),
    ]
    if id_user_ambito is not None:
        condiciones.append(Incident.id_user == id_user_ambito)
    if id_user is not None:
        condiciones.append(Incident.id_user == id_user)
    palabras = _sin_acentos(q).split()
    if palabras:
        articulo, fecha, dias = _expresiones_de_prestamo(hoy)
        pajar = func.lower(func.translate(
            func.concat_ws(" ", articulo, func.coalesce(User.full_name, ""), fecha, cast(dias, String)),
            _CON_ACENTO, _SIN_ACENTO,
        ))
        condiciones.extend(pajar.contains(palabra, autoescape=True) for palabra in palabras)
    return condiciones


def _de_prestamos(columnas):
    return (
        select(*columnas)
        .select_from(NmIncidentProduct)
        .join(Incident, Incident.id_incident == NmIncidentProduct.id_incident)
        .join(Product, Product.id_product == NmIncidentProduct.id_product)
        .outerjoin(IncidentType, IncidentType.id_incident_type == Incident.id_incident_type)
        .outerjoin(User, User.id_user == Incident.id_user)
    )


def _orden_de_prestamos(articulo, orden, direccion, agrupar):
    id_renglon = NmIncidentProduct.id_nm_incident_product
    ascendente = direccion == "asc"
    nombre_responsable = func.lower(func.coalesce(User.full_name, ""))
    if orden == "dias_prestado":
        # Mas dias = fecha mas antigua: el orden por dias es el orden de la fecha, invertido.
        principal = Incident.incident_date.desc() if ascendente else Incident.incident_date.asc()
    elif orden == "fecha_prestamo":
        principal = Incident.incident_date.asc() if ascendente else Incident.incident_date.desc()
    elif orden == "responsable":
        principal = nombre_responsable.asc() if ascendente else nombre_responsable.desc()
    else:  # articulo
        columna = func.lower(articulo)
        principal = columna.asc() if ascendente else columna.desc()
    desempate = [Incident.incident_date.asc(), func.lower(articulo).asc(), id_renglon.asc()]
    if agrupar:
        # Cada responsable contiguo, para que al paginar un grupo no se parta entre dos paginas sin continuar.
        # La direccion elegida ordena los RENGLONES dentro de cada grupo; los grupos van con el prestamo mas
        # viejo primero, salvo que se ordene por responsable: entonces los grupos van A-Z / Z-A.
        if orden == "responsable":
            grupos = [principal, Incident.id_user.asc()]
            dentro = desempate
        else:
            grupos = [
                func.min(Incident.incident_date).over(partition_by=Incident.id_user).asc(),
                nombre_responsable.asc(), Incident.id_user.asc(),
            ]
            dentro = [principal, *desempate]
        return [*grupos, *dentro]
    return [principal, *desempate]


def material_prestado_actual_query(session, *, limit, offset, actor_project=None, id_user=None,
                                   id_user_ambito=None, q=None, orden="dias_prestado", direccion="desc",
                                   agrupar=False):
    """KPI "vivo": renglones de vale actualmente prestados (sin devolver), por responsable.

    No es un KPI de `kpi_snapshot` -- ver `KpiDefinition.modo="vivo"`. Cada
    renglon prestado es un hecho de detalle (que articulo, a quien, desde
    cuando), no un numero por entidad-y-dia: no hay forma correcta de
    comprimirlo en una foto diaria sin perder la fecha exacta de cada
    prestamo. Por eso este query_builder tiene una firma DISTINTA a la de
    los KPIs "snapshot" (sin fecha_inicio/fecha_fin -- siempre es "ahora"; con
    limit/offset -- siempre paginado) y nunca lo llama `tasks_kpis.py`.

    * "Prestado" = dos condiciones, ambas necesarias:
      - Direccion "Salida", y un vale que no sea de BAJA -- ver `TIPOS_DE_BAJA`
        arriba: una Entrada nunca esta prestada, y un vale de Destruccion o
        Extraviado registra que la herramienta ya no esta con nadie, no un
        prestamo pendiente. "Dañado" SI cuenta (ver el comentario de arriba).
        Replicado en SQL, no fila por fila, por el motivo de paginacion ya
        explicado.
      - Sin devolver: `_sin_cerrar(close_date)` -- `close_date IS NULL` o
        `== CIERRE_SENTINELA`, mismo criterio que el resto del modulo.
    * Fecha de prestamo: `Incident.incident_date` (decision explicita para
      este KPI, confirmada contra `migrate_adser.py::migrar_incident`: ese
      campo viene DIRECTO de `fecha_incidente` de origen, sin pasar por
      `normalizar_fecha()`/sentinel -- a diferencia de `fecha_cierre`, que si
      necesito ese tratamiento porque el sistema legado SI usaba un
      placeholder ahi. `fecha_incidente` no tiene ese problema documentado en
      ningun punto de la migracion).
    * "Dias prestado" = hoy - incident_date, calculado en Python al armar
      cada fila.
    * Responsable: `Incident.id_user` (quien levanto el vale), mismo criterio
      que el resto del modulo -- no `created_by`.
    * Sin alcance de proyecto (mismo motivo que sus vecinos de este archivo);
      `actor_project` se acepta por firma pero no se usa aqui.

    Filtros, busqueda y orden se aplican AQUI, en SQL, sobre TODOS los renglones prestados -- no sobre la
    pagina que se pidio: ver `_condiciones_de_prestamo` y `PRESTADO_ORDENES`. Antes el Dashboard pedia las 50
    mas antiguas y filtraba en el navegador, y los vales nuevos (los mas recientes) nunca llegaban.

    Regresa `(items, total)`: `items` ya es la pagina pedida (limit/offset a
    nivel SQL), `total` es el conteo de TODO lo que cumple los filtros, sin paginar (para que el
    frontend pueda mostrar "1-25 de 143").
    """
    hoy = date.today()
    condiciones = _condiciones_de_prestamo(hoy, id_user=id_user, id_user_ambito=id_user_ambito, q=q)
    articulo, _fecha, _dias = _expresiones_de_prestamo(hoy)

    # El total sale de la MISMA pasada que la pagina (`count(*) OVER ()`): con una busqueda de texto, cada
    # pasada sobre los renglones es lo caro, y contar aparte la doblaba.
    filas = session.execute(
        _de_prestamos([
            NmIncidentProduct.id_nm_incident_product, articulo, Incident.id_user, User.full_name,
            Incident.incident_date, func.count().over(),
        ])
        .where(*condiciones)
        .order_by(*_orden_de_prestamos(articulo, orden, direccion, agrupar))
        .limit(limit)
        .offset(offset)
    ).all()
    if filas:
        total = int(filas[0][5])
    elif offset:
        # Una pagina vacia no trae el total en sus filas (se pidio mas alla del final): se cuenta aparte.
        total = session.execute(_de_prestamos([func.count()]).where(*condiciones)).scalar() or 0
    else:
        total = 0

    items = []
    for id_renglon, nombre_articulo, id_usuario, full_name, incident_date, _total in filas:
        items.append({
            "id_nm_incident_product": id_renglon,
            "articulo": nombre_articulo,
            "id_user": id_usuario,
            "responsable": full_name,
            "fecha_prestamo": incident_date.date().isoformat(),
            "dias_prestado": (hoy - incident_date.date()).days,
        })
    return items, total


def material_prestado_actual_resumen_query(session, *, total, id_user=None, id_user_ambito=None, q=None):
    """Los agregados de la tabla, en una consulta cada uno, sin importar cuantos renglones haya.

    * `responsables`: uno por responsable con renglones prestados -- cuantos tiene de verdad y desde hace
      cuantos dias el mas antiguo. UNA pasada con GROUP BY. Es lo que pinta el "(n)" del desplegable y los
      encabezados de la vista "Por responsable". Son independientes de la busqueda y del responsable elegido
      (solo los acota `id_user_ambito`): lo que dice cuanto tiene cada quien no cambia al buscar.
    * `resumen`: de lo que cumple TODOS los filtros -- renglones (el `total` que ya conto la consulta de la
      pagina), responsables distintos y el renglon mas antiguo, estos dos en una sola pasada.

    Con la pagina son 3 consultas en total, constantes: no crecen con los renglones ni con los
    responsables. Solo UNA (la de `resumen` por responsable) evita la busqueda de texto.
    """
    hoy = date.today()
    en_el_ambito = _condiciones_de_prestamo(hoy, id_user_ambito=id_user_ambito)
    filtradas = _condiciones_de_prestamo(hoy, id_user=id_user, id_user_ambito=id_user_ambito, q=q)
    articulo, _fecha, _dias = _expresiones_de_prestamo(hoy)

    por_responsable = session.execute(
        _de_prestamos([Incident.id_user, User.full_name, func.count(), func.min(Incident.incident_date)])
        .where(*en_el_ambito)
        .group_by(Incident.id_user, User.full_name)
        .order_by(func.lower(func.coalesce(User.full_name, "")), Incident.id_user)
    ).all()
    responsables = [
        {
            "id_user": id_usuario, "responsable": full_name, "renglones": int(renglones),
            "mas_antiguo_dias": (hoy - mas_antiguo.date()).days,
        }
        for id_usuario, full_name, renglones, mas_antiguo in por_responsable
    ]

    # Responsables distintos y renglon mas antiguo, en UNA pasada sobre lo filtrado. El mas antiguo sale de
    # un `MIN` sobre una llave de texto que se ordena como (fecha, id): "AAAA-MM-DD" + id con ceros a la
    # izquierda, y despues el responsable y el articulo -- O(n), sin ordenar ni acumular las filas.
    llave = func.concat(
        func.to_char(Incident.incident_date, "YYYY-MM-DD"), func.lpad(cast(NmIncidentProduct.id_nm_incident_product, String), 12, "0"),
        "|", func.coalesce(User.full_name, ""), "|", articulo,
    )
    distintos, mas_antiguo_llave = session.execute(
        _de_prestamos([func.count(func.distinct(func.coalesce(Incident.id_user, 0))), func.min(llave)]).where(*filtradas)
    ).one()
    mas_antiguo = None
    if mas_antiguo_llave:
        fecha_texto, resto = mas_antiguo_llave[:10], mas_antiguo_llave[23:]   # 10 de fecha + 12 de id + "|"
        responsable, _, nombre_articulo = resto.partition("|")
        mas_antiguo = {
            "dias": (hoy - date.fromisoformat(fecha_texto)).days,
            "articulo": nombre_articulo,
            "responsable": responsable or None,
        }
    return {
        "resumen": {"renglones": total, "responsables": int(distintos), "mas_antiguo": mas_antiguo},
        "responsables": responsables,
    }


# Como se llama, en el selector "Agrupar por" del editor, la dimension de un KPI
# cuando el KPI no declara una propia (`etiqueta_dimension`). "global" es un
# KPI sin desglose: su unica "fila" es el total.
ETIQUETA_DIMENSION_POR_OMISION = {d.clave: d.etiqueta for d in CATALOGO_DE_DIMENSIONES}


class KpiDefinition:
    def __init__(self, clave, etiqueta, modulo, dimensiones,
                 query_builder, *, direccion, graficas_permitidas, grafica_default,
                 agregacion=None, unidad="numero", alcance_proyecto=True, modo="snapshot",
                 colores_categoria=None, descripcion=None, etiqueta_dimension=None,
                 orden_categorias=None, limite_categorias=None, resumen_builder=None, sin_asignar=False,
                 etiquetas_categoria=None, ocultar_ceros=False):
        self.clave = clave
        self.etiqueta = etiqueta
        # Una linea corta para el selector de KPI del editor (rediseno del
        # dashboard) -- opcional, sin default obligatorio: un KPI viejo sin
        # descripcion simplemente no muestra esa linea, no revienta nada.
        self.descripcion = descripcion
        # Como se llama lo que se desglosa ("Responsable", "Tecnico"...), para el
        # selector "Agrupar por" del editor. La dimension interna sigue siendo
        # "empleado" (es lo que dice de donde salen los ids), pero un KPI puede
        # tener una etiqueta mas precisa: incidencias_abiertas_por_empleado agrupa
        # por Incident.id_user, quien TIENE el material, y eso es un "Responsable",
        # no cualquier "Empleado". Sin declararla toma la de su dimension.
        self.etiqueta_dimension = etiqueta_dimension or ETIQUETA_DIMENSION_POR_OMISION.get(dimensiones[0], "")
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
        # -- ver GRAFICAS. Obligatorios sin default: un KPI nuevo no se puede
        # quedar sin esta decision tomada. Expuestos por `GET /kpi_definition/`
        # (`app/routes/kpi.py`) para que el frontend los lea directo del
        # registry -- no viven en la tabla `kpi_definition`, no hizo falta
        # migracion para agregarlos.
        self.graficas_permitidas = graficas_permitidas
        self.grafica_default = grafica_default
        # Colores fijos por categoria, solo para KPIs de dimension "estado"
        # con un catalogo cerrado y conocido de antemano (ej.
        # material_por_estado: Entrada/Salida/Danado/Extraviado/Destruccion)
        # -- None para el resto. Se declara aqui, no en el frontend, porque es
        # el mismo tipo de decision de negocio que `direccion`: que color le
        # toca a "Extraviado" no deberia depender de en que orden lleguen las
        # categorias a la grafica. dict {valor_de_categoria: "#rrggbb"}.
        self.colores_categoria = colores_categoria
        # Orden de lectura de las categorias, como LISTA: solo para un KPI de categorias ORDINALES
        # (ej. prestamos_abiertos_por_antiguedad: 0-30, 31-60, 61-90, +90), cuyo orden es parte del
        # dato. Con None (el default, todos los demas) el Dashboard ordena por valor, de mayor a
        # menor. No se deriva de `colores_categoria`: un dict pierde el orden al serializarse.
        self.orden_categorias = tuple(orden_categorias) if orden_categorias else None
        # Nombre visible de cada categoria de una dimension "estado" cuando la clave (la que se guarda en el
        # snapshot) no se lee bien sola, ej. {"por_liberar": "Pagada, aún ocupada"}. None = la clave se muestra
        # capitalizada. `routes/kpi.py` la manda como `etiquetas` junto a los totales.
        self.etiquetas_categoria = dict(etiquetas_categoria) if etiquetas_categoria else None
        # Para una dimension ABIERTA con muchos valores (ej. familia, 41 en Adser): cuantos se
        # muestran, los de mayor valor. El corte se hace al SUMAR el rango (`_totales()` en
        # routes/kpi.py), no en el query_builder: cada dia guarda todas las familias y el top
        # depende del rango que se pida. El "total" sigue siendo el de TODAS. None = sin corte.
        self.limite_categorias = limite_categorias
        # La API no devuelve las entidades cuyo valor es 0 (`por_empleado`). Para una foto por persona ("quien esta en
        # turno ahora"): el job escribe un 0 para quien ya salio, para que el valor viejo no se quede pegado, y ese 0 no
        # debe pintarse como una barra vacia por cada persona que ya se fue. El total no cambia (un cero no suma).
        self.ocultar_ceros = ocultar_ceros
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
        # Solo para un KPI "vivo": calcula los agregados de su tabla (resumen y conteo por responsable) sobre
        # TODOS los renglones, no sobre la pagina pedida. Ver `material_prestado_actual_resumen_query`.
        self.resumen_builder = resumen_builder
        # Si las filas sin entidad (un pedido sin mesero, un viaje sin unidad: `dimension_key` con la
        # llave en NULL) se muestran bajo "Sin asignar" -- en la lista y en el total -- o se descartan,
        # que es lo que `_totales()` hacia siempre. Opt-in: apagada en los 24 KPIs de siempre (ninguno
        # puede devolver entidad nula hoy, y asi sus respuestas no cambian) y encendida en los KPIs de
        # los modulos nuevos, donde la entidad es opcional en el dato (ver `app/kpis/modulos/`). No tiene
        # sentido en dimensiones `global` ni `estado`: `_validar()` lo rechaza.
        self.sin_asignar = sin_asignar


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
        descripcion="Subtotal facturado (antes de impuesto), por empleado y por dia.",
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
        descripcion="Facturas de compra capturadas, por empleado y por dia.",
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
        descripcion="Porcentaje de tareas terminadas, por empleado responsable.",
    ),
    KpiDefinition(
        clave="vales_vencidos_por_responsable",
        etiqueta="Vales vencidos por responsable",
        modulo="operaciones",
        dimensiones=("empleado",),
        etiqueta_dimension="Responsable",
        query_builder=vales_vencidos_por_responsable_query,
        agregacion="suma",
        unidad="numero",
        alcance_proyecto=False,
        direccion="bajo_es_mejor",
        graficas_permitidas=TODAS_LAS_GRAFICAS,
        grafica_default="tabla",
        descripcion="Vales de almacen vencidos y sin cerrar, por responsable.",
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
        descripcion="Porcentaje de incidentes resueltos, por empleado responsable.",
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
        descripcion="Incidentes cancelados, por empleado y por dia de cancelacion.",
    ),
    KpiDefinition(
        clave="ordenes_laboratorio_entregadas_por_tecnico",
        etiqueta="Órdenes de laboratorio entregadas por técnico",
        modulo="laboratorio",
        dimensiones=("empleado",),
        etiqueta_dimension="Técnico",
        query_builder=ordenes_laboratorio_entregadas_por_tecnico_query,
        agregacion="suma",
        unidad="numero",
        direccion="alto_es_mejor",
        graficas_permitidas=TODAS_LAS_GRAFICAS,
        grafica_default="barras",
        descripcion="Ordenes de servicio entregadas, por tecnico.",
    ),
    KpiDefinition(
        clave="tiempo_promedio_reparacion_laboratorio_por_tecnico",
        etiqueta="Tiempo promedio de reparación por técnico",
        modulo="laboratorio",
        dimensiones=("empleado",),
        etiqueta_dimension="Técnico",
        query_builder=tiempo_promedio_reparacion_laboratorio_por_tecnico_query,
        agregacion="promedio_ponderado",
        unidad="dias",
        direccion="bajo_es_mejor",
        graficas_permitidas=TODAS_LAS_GRAFICAS,
        grafica_default="barras",
        descripcion="Dias promedio de reparacion, por tecnico.",
    ),
    KpiDefinition(
        clave="costo_promedio_reparacion_laboratorio_por_tecnico",
        etiqueta="Costo promedio de reparación por técnico",
        modulo="laboratorio",
        dimensiones=("empleado",),
        etiqueta_dimension="Técnico",
        query_builder=costo_promedio_reparacion_laboratorio_por_tecnico_query,
        agregacion="promedio_ponderado",
        unidad="moneda",
        direccion="neutral",
        graficas_permitidas=TODAS_LAS_GRAFICAS,
        grafica_default="barras",
        descripcion="Costo promedio de reparacion, por tecnico.",
    ),
    KpiDefinition(
        clave="documentos_vencidos_por_responsable",
        etiqueta="Documentos vencidos por responsable",
        modulo="documentos",
        dimensiones=("empleado",),
        etiqueta_dimension="Responsable",
        query_builder=documentos_vencidos_por_responsable_query,
        agregacion="suma",
        unidad="numero",
        direccion="bajo_es_mejor",
        graficas_permitidas=TODAS_LAS_GRAFICAS,
        grafica_default="tabla",
        descripcion="Documentos firmados y ya vencidos, por responsable.",
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
        descripcion="Ventas facturadas de toda la empresa, por dia.",
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
        descripcion="Facturas de compra de toda la empresa, por dia.",
    ),
    KpiDefinition(
        clave="material_prestado_por_responsable",
        etiqueta="Material prestado por responsable",
        modulo="inventario",
        dimensiones=("empleado",),
        etiqueta_dimension="Responsable",
        query_builder=material_prestado_por_responsable_query,
        agregacion="suma",
        unidad="numero",
        alcance_proyecto=False,
        direccion="neutral",
        graficas_permitidas=TODAS_LAS_GRAFICAS,
        grafica_default="barras",
        descripcion="Prestamos de material iniciados, por responsable y por dia.",
    ),
    KpiDefinition(
        clave="prestamos_vencidos_por_responsable",
        etiqueta="Préstamos de material vencidos por responsable",
        modulo="inventario",
        dimensiones=("empleado",),
        etiqueta_dimension="Responsable",
        query_builder=prestamos_vencidos_por_responsable_query,
        agregacion="suma",
        unidad="numero",
        alcance_proyecto=False,
        direccion="bajo_es_mejor",
        graficas_permitidas=TODAS_LAS_GRAFICAS,
        grafica_default="tabla",
        descripcion="Piezas prestadas y ya vencidas, por responsable actual.",
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
        descripcion="Lotes de inventario cuya caducidad cae en el rango elegido.",
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
        descripcion="Existencia actual por producto, foto del saldo de hoy.",
    ),
    # --- KPIs nuevos de Adser (almacen de herramientas: lo que importa es
    # cuantas incidencias se abren/cierran, cuanto material esta prestado y
    # donde esta cada articulo -- no "bajo stock", que no aplica a un
    # almacen donde casi toda la existencia es 1). Todos con
    # `alcance_proyecto=False`: un vale/incidencia de almacen no pertenece a
    # un proyecto de cliente, mismo motivo que sus vecinos de este modulo. --
    KpiDefinition(
        clave="incidencias_abiertas_por_empleado",
        etiqueta="Incidencias abiertas por responsable",
        modulo="operaciones",
        dimensiones=("empleado",),
        etiqueta_dimension="Responsable",
        query_builder=incidencias_abiertas_por_empleado_query,
        agregacion="suma",
        unidad="numero",
        alcance_proyecto=False,
        direccion="neutral",
        graficas_permitidas=("barras", "tabla"),
        grafica_default="barras",
        descripcion="Incidencias/vales abiertos, por responsable: el usuario a cuyo nombre esta el material.",
    ),
    KpiDefinition(
        clave="incidencias_pendientes",
        etiqueta="Incidencias pendientes",
        modulo="operaciones",
        dimensiones=("global",),
        query_builder=incidencias_pendientes_query,
        agregacion="ultimo",
        unidad="numero",
        alcance_proyecto=False,
        direccion="bajo_es_mejor",
        graficas_permitidas=("numero",),
        grafica_default="numero",
        descripcion="Foto de cuantas incidencias siguen sin cerrar hoy.",
    ),
    KpiDefinition(
        clave="incidencias_abiertas_vs_cerradas",
        etiqueta="Incidencias abiertas vs. cerradas",
        modulo="operaciones",
        dimensiones=("estado",),
        query_builder=incidencias_abiertas_vs_cerradas_query,
        agregacion="suma",
        unidad="numero",
        alcance_proyecto=False,
        direccion="neutral",
        graficas_permitidas=("barras", "linea"),
        grafica_default="barras",
        # Mismo mecanismo que material_por_estado: colores fijos por valor de
        # categoria, no por posicion -- coral para "abierta" (llama la
        # atencion, hay que atenderla), verde para "cerrada" (resuelta, bien).
        colores_categoria={"abierta": "#ef6f5c", "cerrada": "#22b573"},
        descripcion="Cuantas incidencias se abren y cuantas se cierran, por dia.",
    ),
    KpiDefinition(
        clave="material_por_estado",
        etiqueta="Material por estado",
        modulo="operaciones",
        dimensiones=("estado",),
        query_builder=material_por_estado_query,
        agregacion="suma",
        unidad="numero",
        alcance_proyecto=False,
        direccion="neutral",
        graficas_permitidas=("dona", "tabla"),
        grafica_default="dona",
        # Paleta viva, no oscura (pedido explicito): verde para Entrada,
        # azul para Salida (hecho neutro, no bueno ni malo), ambar/coral para
        # las disposiciones intermedias, y fucsia -no vino- para Destruccion,
        # la mas grave, para que se distinga sin depender de que tan oscuro
        # se vea un tono ya de por si dificil de leer en modo oscuro.
        colores_categoria={
            "Entrada": "#22b573",
            "Salida": "#2f8fe0",
            "Dañado": "#f0a93b",
            "Extraviado": "#ef6f5c",
            "Destruccion": "#e0559b",
        },
        descripcion="Entrada, salida y disposiciones especiales de cada renglon de vale.",
    ),
    KpiDefinition(
        clave="prestamos_abiertos_por_antiguedad",
        etiqueta="Préstamos abiertos por antigüedad",
        modulo="operaciones",
        dimensiones=("estado",),
        etiqueta_dimension="Antigüedad",
        query_builder=prestamos_abiertos_por_antiguedad_query,
        agregacion="ultimo",
        unidad="numero",
        alcance_proyecto=False,
        direccion="bajo_es_mejor",
        graficas_permitidas=("barras", "dona", "tabla"),
        grafica_default="barras",
        # Verde -> ambar -> naranja -> rojo: a mas dias prestado, mas urgente. Por nombre
        # de categoria, como material_por_estado.
        colores_categoria=ANTIGUEDAD_COLORES,
        orden_categorias=ANTIGUEDAD_CATEGORIAS,
        descripcion="Renglones prestados sin devolver, por días desde el vale: 0-30, 31-60, 61-90 y más de 90.",
    ),
    KpiDefinition(
        clave="perdidas_por_familia",
        etiqueta="Pérdidas por familia",
        modulo="operaciones",
        dimensiones=("familia",),
        etiqueta_dimension="Familia",
        query_builder=perdidas_por_familia_query,
        agregacion="suma",
        unidad="piezas",
        alcance_proyecto=False,
        direccion="bajo_es_mejor",
        graficas_permitidas=("barras",),
        grafica_default="barras",
        limite_categorias=10,
        descripcion="Piezas destruidas, extraviadas o dañadas, por familia de producto: las 10 con más pérdidas.",
    ),
    KpiDefinition(
        clave="material_prestado_actual",
        etiqueta="Material prestado ahora",
        modulo="operaciones",
        dimensiones=("empleado",),
        etiqueta_dimension="Responsable",
        query_builder=material_prestado_actual_query,
        resumen_builder=material_prestado_actual_resumen_query,
        modo="vivo",
        unidad="piezas",
        alcance_proyecto=False,
        direccion="neutral",
        graficas_permitidas=("tabla",),
        grafica_default="tabla",
        descripcion="Renglones de vale prestados sin devolver, por responsable.",
    ),
    KpiDefinition(
        clave="piezas_por_estado",
        etiqueta="Piezas por estado",
        modulo="operaciones",
        dimensiones=("estado",),
        etiqueta_dimension="Estado de la pieza",
        query_builder=piezas_por_estado_query,
        agregacion="ultimo",
        unidad="piezas",
        alcance_proyecto=False,
        direccion="neutral",
        graficas_permitidas=("dona", "barras", "tabla"),
        grafica_default="dona",
        colores_categoria=PIEZAS_COLORES,
        orden_categorias=PIEZAS_CATEGORIAS,
        descripcion="Foto de hoy: cuántas piezas están en el almacén, prestadas, en reparación, dañadas, extraviadas o destruidas.",
    ),
)


# KPIs de los modulos nuevos: viven en `app/kpis/modulos/<modulo>.py` y se agregan
# AL FINAL, despues de los de siempre (que no se mueven). Se importan aqui, ya
# definida `KpiDefinition`, porque cada archivo la pide dentro de `definiciones()`.
from app.kpis.modulos import checadas as _checadas  # noqa: E402
from app.kpis.modulos import restaurante as _restaurante  # noqa: E402

KPI_REGISTRY = KPI_REGISTRY + _restaurante.definiciones() + _checadas.definiciones()


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

# Cuantas categorias muestra un KPI de dimension abierta (`limite_categorias`; None = todas): lo
# consume `_totales()` en `app/routes/kpi.py` para cortar al sumar el rango.
LIMITE_POR_CLAVE = {kpi.clave: kpi.limite_categorias for kpi in KPI_REGISTRY}

# Si la API omite las entidades en cero (`KpiDefinition.ocultar_ceros`): lo consume `_totales()` en `routes/kpi.py`.
OCULTAR_CEROS_POR_CLAVE = {kpi.clave: kpi.ocultar_ceros for kpi in KPI_REGISTRY}

# Si el KPI muestra las filas sin entidad como "Sin asignar" (`KpiDefinition.sin_asignar`): lo consume
# `routes/kpi.py` al sumar el rango y al armar las etiquetas.
SIN_ASIGNAR_POR_CLAVE = {kpi.clave: kpi.sin_asignar for kpi in KPI_REGISTRY}

# Y para la regla de agregacion (ver AGREGACIONES): la consume `_totales()` en
# `app/routes/kpi.py` para saber como combinar los snapshots del rango.
AGREGACION_POR_CLAVE = {kpi.clave: kpi.agregacion for kpi in KPI_REGISTRY}

# El objeto KpiDefinition completo por clave -- a diferencia de los mapas de
# arriba (un campo suelto cada uno), este lo necesita el endpoint de KPIs
# "vivo" (`app/routes/kpi.py`) para poder llegar a `.modo` y `.query_builder`
# de un KPI puntual sin repetir la logica de busqueda en KPI_REGISTRY.
KPI_POR_CLAVE = {kpi.clave: kpi for kpi in KPI_REGISTRY}


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
        if not kpi.etiqueta_dimension or len(kpi.etiqueta_dimension) > 30:
            raise RuntimeError(
                f"El KPI '{kpi.clave}' necesita una etiqueta de dimension de 1 a 30 caracteres "
                f"(la dimension '{kpi.dimensiones[0]}' no tiene una por omision)."
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
        if kpi.resumen_builder is not None and kpi.modo != "vivo":
            raise RuntimeError(f"El KPI '{kpi.clave}' declara 'resumen_builder' sin ser de modo 'vivo'.")
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
        if kpi.sin_asignar and CATALOGO_POR_CLAVE[kpi.dimensiones[0]].tipo in ("global", "categoria"):
            raise RuntimeError(
                f"El KPI '{kpi.clave}' pide 'sin_asignar' pero su dimension '{kpi.dimensiones[0]}' "
                "no tiene entidades que puedan faltar."
            )
        if kpi.ocultar_ceros and (kpi.modo != "snapshot" or CATALOGO_POR_CLAVE[kpi.dimensiones[0]].tipo in ("global", "categoria")):
            raise RuntimeError(
                f"El KPI '{kpi.clave}' pide 'ocultar_ceros' pero solo aplica a un KPI snapshot con entidades "
                "(persona o catalogo): en uno global no hay entidad y en uno de categorias un cero es un dato."
            )
        if kpi.limite_categorias is not None and (
            not isinstance(kpi.limite_categorias, int) or isinstance(kpi.limite_categorias, bool)
            or kpi.limite_categorias < 1
        ):
            raise RuntimeError(f"El KPI '{kpi.clave}' declara un limite_categorias que no es un entero positivo.")
        if kpi.orden_categorias is not None:
            if len(set(kpi.orden_categorias)) != len(kpi.orden_categorias):
                raise RuntimeError(f"El KPI '{kpi.clave}' repite una categoria en orden_categorias.")
            if kpi.colores_categoria is not None and set(kpi.orden_categorias) != set(kpi.colores_categoria):
                raise RuntimeError(
                    f"El KPI '{kpi.clave}' declara orden_categorias y colores_categoria con categorias distintas."
                )
        if kpi.etiquetas_categoria is not None:
            if CATALOGO_POR_CLAVE[kpi.dimensiones[0]].tipo != "categoria":
                raise RuntimeError(f"El KPI '{kpi.clave}' declara etiquetas_categoria sin ser de una dimension de categoria.")
            if kpi.orden_categorias is not None and set(kpi.etiquetas_categoria) != set(kpi.orden_categorias):
                raise RuntimeError(f"El KPI '{kpi.clave}' declara etiquetas_categoria y orden_categorias con categorias distintas.")
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
