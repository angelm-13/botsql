"""KPIs de la pestana CRM del Dashboard: clientes, proyectos y tareas.

La pestana junta dos modulos: los de clientes son del modulo `crm` y los de proyectos y tareas del modulo
`operaciones` con `grupo="crm"` (ver `GRUPOS_DE_SELECTOR` en `registry.py`). Su modulo real no cambia: la
licencia, el permiso por rol (`nm_permission_kpi`) y el job siguen leyendo `modulo`.

Ninguno tiene alcance por proyecto (`alcance_proyecto=False`). Un cliente no pertenece a un proyecto, y en un
despliegue donde cada inquilino es un proyecto, quien atiende (recepcion) debe ver TODOS: filtrar por el proyecto
del actor le mostraria solo uno. Tambien es lo unico correcto para un `COUNT(DISTINCT cliente)`: con alcance por
proyecto el job lo correria una vez por proyecto vigente y un cliente con tres proyectos contaria tres veces.

Los KPIs "foto" (`agregacion="ultimo"`) escriben UNA fila por dia, fechada en `fecha_fin`, y SIEMPRE escriben aunque
el valor sea 0: el agregado "ultimo" toma el ultimo dia con filas, y un dia sin fila dejaria visible el valor de un
dia anterior.
"""

from __future__ import annotations

from sqlalchemy import case, func, or_, select

from app.models.customer_supplier import CustomerSupplier
from app.models.proyect import Proyect
from app.services.project_management_service import MANAGEMENT_STATUSES
from app.utils.tiempo import dia_local, hoy_negocio

# `customer_supplier.type`: la misma tabla guarda clientes y proveedores. Un KPI de clientes cuenta solo los primeros.
TIPO_CLIENTE = "client"

# `proyect.proyect_status` (el recorrido del taller) que NO cuentan como un proyecto vivo para decir que un cliente
# esta activo: terminado (`completed`), rechazado (`denied`) y el borrador que todavia no se entrega (`draft`).
# Los demas cuentan, incluidos `blocked` y `stopped`: el proyecto sigue abierto aunque este detenido.
ESTATUS_DE_PROYECTO_QUE_NO_ACTIVA = ("completed", "denied", "draft")

# `proyect.management_status` (la vida comercial) que saca a un proyecto de lo vivo. Admite NULL: un NULL NO es cancelado.
ESTATUS_COMERCIAL_CANCELADO = "cancelado"

# `proyect.proyect_status` con los que un proyecto YA NO puede estar vencido de entrega: terminado (`completed`),
# recolectado (`collected`, el ultimo paso antes de terminar) o rechazado (`denied`). `blocked` y `stopped` SI cuentan: un
# proyecto detenido al que se le paso la fecha esta vencido.
ESTATUS_DE_PROYECTO_SIN_ENTREGA_PENDIENTE = ("completed", "collected", "denied")

# Categoria de lo que no tiene estado o trae uno fuera del catalogo (dato viejo, captura manual): se cuenta aparte en vez
# de perderse o de contarse como otra cosa.
SIN_ESTADO = "sin_estado"
COLOR_SIN_ESTADO = "#a9b7c9"
ETIQUETA_SIN_ESTADO = "Sin estado"


def _es_hoy(fecha_fin) -> bool:
    """Una foto de AHORA solo se emite si el rango termina hoy (dia del negocio).

    Un backfill sobre un rango pasado escribiria el estado de hoy con la fecha de ese rango, una foto inventada: el
    estado de un cliente, proyecto o tarea en una fecha pasada no se puede reconstruir (no hay historia de estados).
    """
    return fecha_fin == hoy_negocio()


# --- clientes ----------------------------------------------------------------------------------

def clientes_nuevos_query(session, fecha_inicio, fecha_fin, filtros_dimension, actor_project):
    """Clientes dados de alta por dia (`type='client'`), segun `creation_date`.

    * Solo clientes (`TIPO_CLIENTE`): los proveedores no cuentan, ni un `type` NULL (la columna lo admite).
    * Vigencia: `deletion_date IS NULL`.
    * Fecha: el DIA del negocio de `creation_date` (UTC), con `dia_local`: un alta a las 20:00 de Mexico se guarda
      como 02:00 UTC del dia siguiente y `date()` la contaria un dia tarde. Un `creation_date` NULL (lo que dejan
      las migraciones directas de un sistema anterior) no tiene dia y queda fuera.
    * Un dia sin altas no genera fila: con `agregacion="suma"` no hace falta.
    * Es un flujo, no una foto: la API suma los dias del rango. Para "por mes" se pide el rango de ese mes y se toma
      el total (o la barra de cada dia); el Dashboard no agrupa por mes.

    Dimension "global". Sin alcance de proyecto: `customer_supplier` no tiene `id_proyect`.
    """
    dia = dia_local(CustomerSupplier.creation_date)
    stmt = (
        select(dia.label("dia"), func.count(CustomerSupplier.id_customer_supplier))
        .where(
            CustomerSupplier.deletion_date.is_(None),
            CustomerSupplier.type == TIPO_CLIENTE,
            CustomerSupplier.creation_date.isnot(None),
            dia >= fecha_inicio,
            dia <= fecha_fin,
        )
        .group_by(dia)
        .order_by(dia)
    )
    return [(None, fecha, total) for fecha, total in session.execute(stmt).all()]


def clientes_activos_query(session, fecha_inicio, fecha_fin, filtros_dimension, actor_project):
    """Foto de hoy: clientes distintos con al menos un proyecto vivo.

    Un cliente esta activo si es `type='client'`, no esta dado de baja y tiene al menos un proyecto vigente
    (`deletion_date IS NULL`) cuyo `proyect_status` NO es `completed`, `denied` ni `draft`
    (`ESTATUS_DE_PROYECTO_QUE_NO_ACTIVA`) y cuyo `management_status` no es `cancelado`. `blocked` y `stopped` cuentan.

    `COUNT(DISTINCT id_customer_supplier)`, calculado UNA sola vez sobre todos los proyectos: un cliente con tres
    proyectos vivos cuenta uno. Por eso `alcance_proyecto=False` (ver el docstring del archivo).

    `management_status` admite NULL: `NOT IN`/`!=` contra NULL no es verdadero, asi que un proyecto sin estado comercial
    se descartaria por error; se pide expresamente `IS NULL OR != 'cancelado'`.

    Es una foto del estado de hoy, no una reconstruccion: una fila fechada en `fecha_fin`, aunque sea 0, y solo si
    `fecha_fin` es hoy (`_es_hoy`).
    """
    if not _es_hoy(fecha_fin):
        return []
    stmt = (
        select(func.count(func.distinct(Proyect.id_customer_supplier)))
        .select_from(Proyect)
        .join(CustomerSupplier, CustomerSupplier.id_customer_supplier == Proyect.id_customer_supplier)
        .where(
            CustomerSupplier.deletion_date.is_(None),
            CustomerSupplier.type == TIPO_CLIENTE,
            Proyect.deletion_date.is_(None),
            Proyect.proyect_status.notin_(ESTATUS_DE_PROYECTO_QUE_NO_ACTIVA),
            or_(Proyect.management_status.is_(None), Proyect.management_status != ESTATUS_COMERCIAL_CANCELADO),
        )
    )
    return [(None, fecha_fin, session.scalar(stmt) or 0)]


# --- proyectos ---------------------------------------------------------------------------------

# Estado comercial (`proyect.management_status`), en el orden en que se leen. Las claves son las del catalogo del servicio
# (`MANAGEMENT_STATUSES`); las etiquetas son neutrales: sirven igual a un taller, una obra o un despacho.
COMERCIAL_CATEGORIAS = (*MANAGEMENT_STATUSES, SIN_ESTADO)
COMERCIAL_ETIQUETAS = {
    "pendiente_orden_compra": "Pendiente de orden de compra",
    "autorizado": "Autorizado",
    "cancelado": "Cancelado",
    "cobrado": "Cobrado",
    SIN_ESTADO: ETIQUETA_SIN_ESTADO,
}
# Ambar (falta algo), azul (en marcha), coral (se cayo), verde (cobrado) y gris azulado para lo sin estado.
COMERCIAL_COLORES = {
    "pendiente_orden_compra": "#f0a93b",
    "autorizado": "#2f8fe0",
    "cancelado": "#ef6f5c",
    "cobrado": "#22b573",
    SIN_ESTADO: COLOR_SIN_ESTADO,
}


def proyectos_por_estado_comercial_query(session, fecha_inicio, fecha_fin, filtros_dimension, actor_project):
    """Foto de hoy: proyectos vigentes por estado comercial (`proyect.management_status`).

    * Vigencia: `deletion_date IS NULL`. Cuenta proyectos de cualquier cliente y de cualquier estado de taller.
    * Siempre regresa las cuatro categorias del catalogo, con 0 cuando no hay: el agregado "ultimo" toma el ultimo dia
      con filas, y una categoria ausente se lee como "no calculada", no como cero.
    * Un `management_status` NULL (la columna lo admite) o fuera del catalogo se cuenta en `sin_estado`, que solo sale
      cuando hay alguno: no ensucia la dona con una rebanada vacia.
    * Foto de AHORA: solo se emite si `fecha_fin` es hoy (`_es_hoy`); no hay historia de estados para reconstruir un dia pasado.

    Dimension "estado" (categoria). Sin alcance de proyecto: es un conteo de todos los proyectos.
    """
    if not _es_hoy(fecha_fin):
        return []
    categoria = case((Proyect.management_status.in_(MANAGEMENT_STATUSES), Proyect.management_status), else_=SIN_ESTADO)
    stmt = (
        select(categoria.label("categoria"), func.count(Proyect.id_proyect))
        .where(Proyect.deletion_date.is_(None))
        .group_by(categoria)
    )
    conteos = dict(session.execute(stmt).all())
    categorias = [*MANAGEMENT_STATUSES, *([SIN_ESTADO] if conteos.get(SIN_ESTADO) else [])]
    return [(categoria, fecha_fin, conteos.get(categoria, 0)) for categoria in categorias]


def proyectos_con_entrega_vencida_query(session, fecha_inicio, fecha_fin, filtros_dimension, actor_project):
    """Foto de hoy: proyectos vigentes cuya fecha de entrega (`delivery_date`) ya paso y siguen abiertos.

    Vencido = `delivery_date` anterior a hoy (el mismo dia de la entrega todavia no esta vencido) y el proyecto no esta
    terminado, recolectado ni rechazado (`ESTATUS_DE_PROYECTO_SIN_ENTREGA_PENDIENTE`) ni cancelado comercialmente
    (`management_status = 'cancelado'`; un NULL no es cancelado). Un proyecto bloqueado o detenido SI cuenta.
    Un proyecto sin `delivery_date` nunca vence: no hay fecha que se haya pasado.

    Siempre escribe una fila (0 si nada esta vencido) y solo si `fecha_fin` es hoy (`_es_hoy`).
    Dimension "global". Sin alcance de proyecto.
    """
    if not _es_hoy(fecha_fin):
        return []
    stmt = select(func.count(Proyect.id_proyect)).where(
        Proyect.deletion_date.is_(None),
        Proyect.delivery_date.isnot(None),
        Proyect.delivery_date < fecha_fin,
        Proyect.proyect_status.notin_(ESTATUS_DE_PROYECTO_SIN_ENTREGA_PENDIENTE),
        or_(Proyect.management_status.is_(None), Proyect.management_status != ESTATUS_COMERCIAL_CANCELADO),
    )
    return [(None, fecha_fin, session.scalar(stmt) or 0)]


# --- definiciones ------------------------------------------------------------------------------

def definiciones():
    from app.kpis.registry import KpiDefinition

    return (
        KpiDefinition(
            clave="clientes_nuevos",
            etiqueta="Clientes nuevos",
            modulo="crm",
            grupo="crm",
            dimensiones=("global",),
            query_builder=clientes_nuevos_query,
            agregacion="suma",
            unidad="numero",
            alcance_proyecto=False,
            direccion="alto_es_mejor",
            graficas_permitidas=("barras", "linea", "numero"),
            grafica_default="barras",
            descripcion=(
                "Clientes dados de alta por día (solo tipo cliente, sin proveedores). Elige el rango de un mes para ver "
                "los de ese mes: el total del rango es la suma de sus días."
            ),
        ),
        KpiDefinition(
            clave="clientes_activos",
            etiqueta="Clientes activos",
            modulo="crm",
            grupo="crm",
            dimensiones=("global",),
            query_builder=clientes_activos_query,
            agregacion="ultimo",
            unidad="numero",
            alcance_proyecto=False,
            direccion="neutral",
            graficas_permitidas=("numero", "linea"),
            grafica_default="numero",
            descripcion=(
                "Foto de hoy: clientes con al menos un proyecto vivo, es decir, que no está terminado, rechazado, en "
                "borrador ni cancelado. Un proyecto bloqueado o detenido cuenta. Un cliente con varios proyectos cuenta una vez."
            ),
        ),
        KpiDefinition(
            clave="proyectos_por_estado_comercial",
            etiqueta="Proyectos por estado comercial",
            modulo="operaciones",
            grupo="crm",
            dimensiones=("estado",),
            etiqueta_dimension="Estado comercial",
            query_builder=proyectos_por_estado_comercial_query,
            agregacion="ultimo",
            unidad="numero",
            alcance_proyecto=False,
            direccion="neutral",
            graficas_permitidas=("dona", "barras"),
            grafica_default="dona",
            colores_categoria=COMERCIAL_COLORES,
            orden_categorias=COMERCIAL_CATEGORIAS,
            etiquetas_categoria=COMERCIAL_ETIQUETAS,
            descripcion=(
                "Foto de hoy: cuántos proyectos hay pendientes de orden de compra, autorizados, cancelados y cobrados. "
                "«Sin estado» solo sale si algún proyecto no lo tiene."
            ),
        ),
        KpiDefinition(
            clave="proyectos_con_entrega_vencida",
            etiqueta="Proyectos con entrega vencida",
            modulo="operaciones",
            grupo="crm",
            dimensiones=("global",),
            query_builder=proyectos_con_entrega_vencida_query,
            agregacion="ultimo",
            unidad="numero",
            alcance_proyecto=False,
            direccion="bajo_es_mejor",
            graficas_permitidas=("numero", "linea"),
            grafica_default="numero",
            descripcion=(
                "Foto de hoy: proyectos cuya fecha de entrega ya pasó y siguen abiertos. No cuentan los terminados, "
                "recolectados, rechazados ni cancelados; uno bloqueado o detenido sí."
            ),
        ),
    )
