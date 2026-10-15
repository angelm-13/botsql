"""KPIs del restaurante (tablas `restaurant_*`).

Todos comparten las reglas de `app/services/restaurant_rules.py` -- la venta, el importe de
un renglon, el subtotal de una orden -- que son las mismas que usan el corte de caja y los
reportes del servicio, y tienen alcance por proyecto: toda tabla `restaurant_*` trae
`id_proyect NOT NULL`.

Cada consulta regresa `(entidad, fecha, valor[, peso])` (ver `AGREGACIONES` en `registry.py`):
una fila por dia y por entidad, solo para los dias que tienen datos. Un dia sin ordenes no
genera fila, asi que ningun promedio divide entre cero y "sin datos" es "sin filas".

Los KPIs con entidad opcional (una orden puede no tener mesero) declaran `sin_asignar=True`:
esas filas salen como "Sin asignar" en la lista y cuentan en el total.

Sobre `filtros_dimension`: es el cuarto argumento de la firma comun de un `query_builder`, pero
la tarea nocturna siempre manda `{}` (el recorte por persona/entidad se hace al LEER, en
`routes/kpi.py`), asi que estas consultas no lo usan.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import and_, case, exists, func, select

from app.models.restaurant import (
    RestaurantCashSession, RestaurantOrder, RestaurantOrderItem, RestaurantTable, RestaurantVisit,
)
from app.utils.tiempo import dia_local
from app.services.restaurant_rules import (
    ESTADO_DE_VENTA, condiciones_de_venta, importe_de_renglon, subtotal_por_orden,
)

CENTAVOS = Decimal("0.01")

# Estatus con el que el corte de caja cierra una sesion (`RestaurantService.close_cash_session`).
SESION_CERRADA = "closed"


def _por_proyecto(condiciones: list, columna, actor_project) -> list:
    if actor_project is not None:
        condiciones.append(columna == actor_project)
    return condiciones


def _renglones_vendidos(session, fecha_inicio, fecha_fin, actor_project, columnas_de_grupo, agregado, *, visita=False):
    """`agregado` sobre los renglones de las ordenes cobradas, por dia de cobro y `columnas_de_grupo`."""
    fecha_col = dia_local(RestaurantOrder.paid_at)
    condiciones = _por_proyecto(
        [*condiciones_de_venta(), fecha_col >= fecha_inicio, fecha_col <= fecha_fin],
        RestaurantOrder.id_proyect, actor_project,
    )
    stmt = (
        select(*columnas_de_grupo, fecha_col.label("fecha"), agregado)
        .select_from(RestaurantOrderItem)
        .join(RestaurantOrder, RestaurantOrder.id_restaurant_order == RestaurantOrderItem.id_restaurant_order)
    )
    if visita:
        stmt = stmt.join(RestaurantVisit, RestaurantVisit.id_restaurant_visit == RestaurantOrder.id_restaurant_visit)
    stmt = (
        stmt.where(*condiciones)
        .group_by(*columnas_de_grupo, fecha_col)
        .order_by(*columnas_de_grupo, fecha_col)
    )
    return session.execute(stmt).all()


def _ordenes_cobradas_por_dia(session, fecha_inicio, fecha_fin, actor_project):
    """`(fecha, subtotal de las ordenes, propinas, numero de ordenes)` por dia de cobro."""
    sub = subtotal_por_orden()
    fecha_col = dia_local(RestaurantOrder.paid_at)
    condiciones = _por_proyecto(
        [*condiciones_de_venta(), fecha_col >= fecha_inicio, fecha_col <= fecha_fin],
        RestaurantOrder.id_proyect, actor_project,
    )
    stmt = (
        select(
            fecha_col.label("fecha"),
            func.coalesce(func.sum(func.coalesce(sub.c.subtotal, 0)), 0),
            func.coalesce(func.sum(RestaurantOrder.tip_amount), 0),
            func.count(RestaurantOrder.id_restaurant_order),
        )
        .select_from(RestaurantOrder)
        .outerjoin(sub, sub.c.id_restaurant_order == RestaurantOrder.id_restaurant_order)
        .where(*condiciones)
        .group_by(fecha_col)
        .order_by(fecha_col)
    )
    return session.execute(stmt).all()


# --- ventas -------------------------------------------------------------------------------

def ventas_restaurante_query(session, fecha_inicio, fecha_fin, filtros_dimension, actor_project):
    """Ventas del restaurante por dia de cobro, SIN desglose.

    * Venta: orden `pagado` y no borrada (`restaurant_rules.condiciones_de_venta`).
    * Importe: `cantidad x precio unitario` de cada renglon, sin propina.
    * Dia: `paid_at`.
    * Dimension "global": cada fila regresa `None` como entidad.
    """
    filas = _renglones_vendidos(session, fecha_inicio, fecha_fin, actor_project, (), func.sum(importe_de_renglon()))
    return [(None, fecha, total) for fecha, total in filas]


def ventas_por_mesero_query(session, fecha_inicio, fecha_fin, filtros_dimension, actor_project):
    """Ventas del restaurante por mesero y por dia de cobro.

    Misma regla que `ventas_restaurante_query`. El mesero es el de la ORDEN
    (`restaurant_order.id_restaurant_waiter`, que se copia de la visita al abrirla). Una orden
    sin mesero regresa `None` y el Dashboard la muestra como "Sin asignar": no se descarta,
    para que el total siga cuadrando con las ventas.
    """
    return list(_renglones_vendidos(
        session, fecha_inicio, fecha_fin, actor_project,
        (RestaurantOrder.id_restaurant_waiter,), func.sum(importe_de_renglon()),
    ))


def ticket_promedio_query(session, fecha_inicio, fecha_fin, filtros_dimension, actor_project):
    """Ticket promedio: subtotal vendido entre el numero de ordenes cobradas, por dia de cobro.

    Cuatro columnas: el `peso` es el numero de ordenes de ese dia, asi que el promedio de
    cualquier rango se reconstruye exacto (`promedio_ponderado`: Σ ticket·ordenes / Σ ordenes
    = Σ subtotal / Σ ordenes). Divide entre TODAS las ordenes cobradas, tengan renglones o no,
    igual que `RestaurantService.kpis()["avg_ticket"]`. Un dia sin ordenes no tiene fila: nunca
    se divide entre cero.
    """
    return [
        (None, fecha, (Decimal(subtotal) / ordenes).quantize(CENTAVOS), ordenes)
        for fecha, subtotal, _propinas, ordenes in _ordenes_cobradas_por_dia(session, fecha_inicio, fecha_fin, actor_project)
        if ordenes
    ]


# --- propinas (de la orden, repartidas entre todos: NUNCA por mesero) ---------------------------

def propinas_restaurante_query(session, fecha_inicio, fecha_fin, filtros_dimension, actor_project):
    """Propinas cobradas por dia de cobro, SIN desglose.

    `restaurant_order.tip_amount` de las ordenes que son venta. Una propina no especificada
    vale 0 (la columna es NOT NULL con ese valor). No hay version por mesero a proposito: las
    propinas se reparten entre todo el personal, no son del mesero que atendio.
    """
    return [
        (None, fecha, Decimal(propinas))
        for fecha, _subtotal, propinas, ordenes in _ordenes_cobradas_por_dia(session, fecha_inicio, fecha_fin, actor_project)
        if ordenes
    ]


def propina_pct_de_venta_query(session, fecha_inicio, fecha_fin, filtros_dimension, actor_project):
    """Propina como porcentaje de la venta (subtotal), por dia de cobro.

    `Σ propinas / Σ subtotal x 100`. El `peso` es el subtotal del dia: asi el porcentaje de un
    rango es `Σ propinas / Σ subtotal` real (`promedio_ponderado`), no el promedio de los
    porcentajes diarios. Un dia sin venta (subtotal 0) no genera fila: nunca se divide entre cero.
    """
    filas = []
    for fecha, subtotal, propinas, _ordenes in _ordenes_cobradas_por_dia(session, fecha_inicio, fecha_fin, actor_project):
        subtotal = Decimal(subtotal)
        if subtotal > 0:
            filas.append((None, fecha, (Decimal(propinas) * 100 / subtotal).quantize(CENTAVOS), subtotal))
    return filas


# --- platillos y mesas ----------------------------------------------------------------------

def platillos_mas_vendidos_query(session, fecha_inicio, fecha_fin, filtros_dimension, actor_project):
    """Cantidad de cada platillo vendido (`Σ quantity`), por dia de cobro. El top 10 se corta al leer."""
    return [
        (id_platillo, fecha, int(cantidad))
        for id_platillo, fecha, cantidad in _renglones_vendidos(
            session, fecha_inicio, fecha_fin, actor_project,
            (RestaurantOrderItem.id_restaurant_dish,), func.sum(RestaurantOrderItem.quantity),
        )
    ]


def frecuencia_por_platillo_query(session, fecha_inicio, fecha_fin, filtros_dimension, actor_project):
    """En cuantas ordenes DISTINTAS aparece cada platillo, por dia de cobro.

    Distinto de `platillos_mas_vendidos`: un platillo pedido 5 veces en una sola orden suma 5
    alla y 1 aqui. Una orden se cobra en un solo dia, asi que sumar los dias no cuenta dos veces.
    """
    return [
        (id_platillo, fecha, int(ordenes))
        for id_platillo, fecha, ordenes in _renglones_vendidos(
            session, fecha_inicio, fecha_fin, actor_project,
            (RestaurantOrderItem.id_restaurant_dish,), func.count(func.distinct(RestaurantOrderItem.id_restaurant_order)),
        )
    ]


def top_mesas_query(session, fecha_inicio, fecha_fin, filtros_dimension, actor_project):
    """Venta (subtotal) por mesa y por dia de cobro.

    La mesa sale de la VISITA de la orden: `restaurant_order.id_restaurant_visit` →
    `restaurant_visit.id_restaurant_table`. Una visita "para llevar" no tiene mesa (el CHECK
    `ck_restaurant_visit_service_type` solo exige mesa a las de servicio en mesa) y por eso
    se deja fuera: este KPI mide mesas, no el mostrador. (El `top_tables` del servicio cuenta
    servicios por mesa; este suma venta.)
    """
    filas = _renglones_vendidos(
        session, fecha_inicio, fecha_fin, actor_project,
        (RestaurantVisit.id_restaurant_table,), func.sum(importe_de_renglon()), visita=True,
    )
    return [(id_mesa, fecha, total) for id_mesa, fecha, total in filas if id_mesa is not None]


# --- servicio -------------------------------------------------------------------------------

def servicios_por_mesero_query(session, fecha_inicio, fecha_fin, filtros_dimension, actor_project):
    """Ordenes enviadas a cocina por mesero, por dia de envio (`sent_at`).

    Un servicio es una orden que salio de `borrador` (`sent_at` no nulo), se cobre o no: mide
    cuanto atendio cada mesero, no cuanto vendio. Las ordenes borradas no cuentan.
    """
    fecha_col = dia_local(RestaurantOrder.sent_at)
    condiciones = _por_proyecto(
        [
            RestaurantOrder.deletion_date.is_(None),
            RestaurantOrder.sent_at.isnot(None),
            fecha_col >= fecha_inicio,
            fecha_col <= fecha_fin,
        ],
        RestaurantOrder.id_proyect, actor_project,
    )
    stmt = (
        select(RestaurantOrder.id_restaurant_waiter, fecha_col.label("fecha"), func.count(RestaurantOrder.id_restaurant_order))
        .where(*condiciones)
        .group_by(RestaurantOrder.id_restaurant_waiter, fecha_col)
        .order_by(RestaurantOrder.id_restaurant_waiter, fecha_col)
    )
    return [(id_mesero, fecha, int(ordenes)) for id_mesero, fecha, ordenes in session.execute(stmt).all()]


def tiempo_de_entrega_query(session, fecha_inicio, fecha_fin, filtros_dimension, actor_project):
    """Minutos promedio entre "lista para entrega" y "entregado" (`ready_at` → `delivered_at`).

    Por ORDEN (el restaurante marca los tiempos por orden, no por renglon). Solo ordenes con
    AMBAS marcas, por dia de entrega, con el numero de ordenes como `peso`
    (`promedio_ponderado`). Es la misma medicion que `RestaurantService.kpis()` llama
    `avg_minutes_from_ready_to_delivered`, con una diferencia: el servicio promedia solo las
    ordenes ya COBRADAS y esta cuenta toda orden entregada (una entregada sin cobrar todavia
    midio su tiempo de entrega).
    """
    fecha_col = dia_local(RestaurantOrder.delivered_at)
    minutos = func.extract("epoch", RestaurantOrder.delivered_at - RestaurantOrder.ready_at) / 60.0
    condiciones = _por_proyecto(
        [
            RestaurantOrder.deletion_date.is_(None),
            RestaurantOrder.ready_at.isnot(None),
            RestaurantOrder.delivered_at.isnot(None),
            fecha_col >= fecha_inicio,
            fecha_col <= fecha_fin,
        ],
        RestaurantOrder.id_proyect, actor_project,
    )
    stmt = (
        select(fecha_col.label("fecha"), func.avg(minutos), func.count(RestaurantOrder.id_restaurant_order))
        .where(*condiciones)
        .group_by(fecha_col)
        .order_by(fecha_col)
    )
    return [
        (None, fecha, Decimal(promedio).quantize(CENTAVOS), ordenes)
        for fecha, promedio, ordenes in session.execute(stmt).all()
    ]


# --- caja ---------------------------------------------------------------------------------

def diferencia_de_caja_query(session, fecha_inicio, fecha_fin, filtros_dimension, actor_project):
    """Desviacion de caja: suma de |difference| de cada sesion cerrada, por cajero y por dia de cierre.

    * `restaurant_cash_session.difference` = lo contado menos lo esperado
      (`RestaurantService.close_cash_session`): negativo es faltante, positivo es sobrante.
    * Sobrante y faltante pesan igual: se toma el valor absoluto POR SESION y despues se suma, no
      el absoluto de la suma, para que +100 y -100 del mismo dia den 200 y no se compensen.
    * Solo sesiones `closed` y no borradas; el dia es el de `closed_at`.
    * Cajero: `closed_by_id` (un usuario).
    * La clave sigue siendo `diferencia_de_caja` (el seed no borra filas: un renombre dejaria una huerfana).
    """
    fecha_col = dia_local(RestaurantCashSession.closed_at)
    condiciones = _por_proyecto(
        [
            RestaurantCashSession.deletion_date.is_(None),
            RestaurantCashSession.status == SESION_CERRADA,
            RestaurantCashSession.closed_at.isnot(None),
            RestaurantCashSession.difference.isnot(None),
            fecha_col >= fecha_inicio,
            fecha_col <= fecha_fin,
        ],
        RestaurantCashSession.id_proyect, actor_project,
    )
    stmt = (
        select(RestaurantCashSession.closed_by_id, fecha_col.label("fecha"), func.sum(func.abs(RestaurantCashSession.difference)))
        .where(*condiciones)
        .group_by(RestaurantCashSession.closed_by_id, fecha_col)
        .order_by(RestaurantCashSession.closed_by_id, fecha_col)
    )
    return session.execute(stmt).all()


# --- fotos del dia en curso (agregacion "ultimo") ----------------------------------------------
#
# Las tres leen el estado de AHORA, no un periodo: `fecha_inicio` se ignora y la foto se fecha en
# `fecha_fin`. La corrida frecuente (`app/kpis/frecuencia.py`) las repite cada pocos minutos solo para hoy.
# Siempre regresan TODAS sus categorias, con 0 si no hay nada: una categoria ausente se leeria como
# "no calculada". Ninguna usa `sin_asignar`: sus categorias son texto fijo, no entidades que puedan faltar.

PEDIDO_COBRADO = "cobrado"
PEDIDO_ENTREGADO_SIN_COBRAR = "entregado_sin_cobrar"
PEDIDO_EN_CURSO = "en_curso"
PEDIDOS_CATEGORIAS = (PEDIDO_COBRADO, PEDIDO_ENTREGADO_SIN_COBRAR, PEDIDO_EN_CURSO)
PEDIDOS_COLORES = {PEDIDO_COBRADO: "#22b573", PEDIDO_ENTREGADO_SIN_COBRAR: "#f0a93b", PEDIDO_EN_CURSO: "#2f8fe0"}
# Estatus de una orden que ya salio de `borrador` y todavia no se entrega (`ORDER_TRANSITIONS` del servicio).
ESTATUS_EN_CURSO = ("pedido", "en_preparacion", "listo_para_entrega")
ESTATUS_ENTREGADO = "entregado"
ESTATUS_BORRADOR = "borrador"

MESA_LIBRE = "libre"
MESA_CON_CUENTA_PENDIENTE = "ocupada_con_cuenta_pendiente"
MESA_POR_LIBERAR = "por_liberar"
MESAS_CATEGORIAS = (MESA_LIBRE, MESA_CON_CUENTA_PENDIENTE, MESA_POR_LIBERAR)
MESAS_ETIQUETAS = {
    MESA_LIBRE: "Libre",
    MESA_CON_CUENTA_PENDIENTE: "Ocupada con cuenta pendiente",
    MESA_POR_LIBERAR: "Pagada, aún ocupada",
}
MESAS_COLORES = {MESA_LIBRE: "#22b573", MESA_CON_CUENTA_PENDIENTE: "#ef6f5c", MESA_POR_LIBERAR: "#2f8fe0"}


def pedidos_del_dia_query(session, fecha_inicio, fecha_fin, filtros_dimension, actor_project):
    """Pedidos HECHOS en `fecha_fin`, en tres categorias que no se traslapan segun su estatus de ahora.

    * Pedido hecho: orden no borrada que ya salio de `borrador`, y cuyo dia de envio a cocina
      (`sent_at`; `started_at` si falta) es `fecha_fin`. Un `borrador` no cuenta.
    * `cobrado` = `pagado`; `entregado_sin_cobrar` = `entregado`; `en_curso` = `pedido`,
      `en_preparacion` o `listo_para_entrega`.
    * La suma de las tres es el total de pedidos hechos ese dia. Se agrupa por el dia en que se HIZO el
      pedido, no por el de cobro (para eso esta `ventas_restaurante`): una orden enviada ayer y cobrada hoy
      es de ayer.
    """
    dia = dia_local(func.coalesce(RestaurantOrder.sent_at, RestaurantOrder.started_at))
    categoria = case(
        (RestaurantOrder.status == ESTADO_DE_VENTA, PEDIDO_COBRADO),
        (RestaurantOrder.status == ESTATUS_ENTREGADO, PEDIDO_ENTREGADO_SIN_COBRAR),
        else_=PEDIDO_EN_CURSO,
    )
    condiciones = _por_proyecto(
        [
            RestaurantOrder.deletion_date.is_(None),
            RestaurantOrder.status.in_((ESTADO_DE_VENTA, ESTATUS_ENTREGADO, *ESTATUS_EN_CURSO)),
            dia == fecha_fin,
        ],
        RestaurantOrder.id_proyect, actor_project,
    )
    stmt = select(categoria, func.count(RestaurantOrder.id_restaurant_order)).where(*condiciones).group_by(categoria)
    conteos = {cat: int(n) for cat, n in session.execute(stmt).all()}
    return [(cat, fecha_fin, conteos.get(cat, 0)) for cat in PEDIDOS_CATEGORIAS]


def cuentas_sin_cobrar_query(session, fecha_inicio, fecha_fin, filtros_dimension, actor_project):
    """Monto (subtotal, sin propina) de las ordenes ENTREGADAS que todavia no se cobran, de cualquier dia.

    Es el dinero que el cliente ya consumio y aun no entra a la caja: explica una desviacion de caja (la
    caja espera lo cobrado, no lo entregado). Es un saldo, no un periodo: una cuenta entregada ayer y sin
    cobrar sigue contando hoy. Mismo importe que la venta (`importe_de_renglon`), asi que al cobrarse pasa
    tal cual a `ventas_restaurante`.
    """
    sub = subtotal_por_orden()
    condiciones = _por_proyecto(
        [RestaurantOrder.deletion_date.is_(None), RestaurantOrder.status == ESTATUS_ENTREGADO],
        RestaurantOrder.id_proyect, actor_project,
    )
    stmt = (
        select(func.coalesce(func.sum(func.coalesce(sub.c.subtotal, 0)), 0))
        .select_from(RestaurantOrder)
        .outerjoin(sub, sub.c.id_restaurant_order == RestaurantOrder.id_restaurant_order)
        .where(*condiciones)
    )
    return [(None, fecha_fin, Decimal(session.scalar(stmt)).quantize(CENTAVOS))]


def mesas_ocupadas_query(session, fecha_inicio, fecha_fin, filtros_dimension, actor_project):
    """Estado de las mesas activas AHORA: libre, ocupada con cuenta pendiente, o pagada y aun ocupada.

    Una mesa se libera cuando el mesero CIERRA la visita (`RestaurantService.close_visit`), NO al cobrar:
    `pay_order` y `pay_visit` solo marcan la orden `pagado` y la visita sigue `active` hasta que alguien la
    cierra. Las categorias no se traslapan:
    * `por_liberar` ("Pagada, aun ocupada"): visita `active` con al menos UNA orden (no borrada, y sin contar
      borradores vacios) y TODAS pagadas. Si el mesero no la cierra, sigue apareciendo asi.
    * `ocupada_con_cuenta_pendiente`: el resto de las visitas `active`: alguna orden sin pagar, o ninguna
      orden todavia (recien sentados). Un `borrador` sin partidas se IGNORA (no es una orden ni retiene la mesa).
    * `libre`: mesa activa y no borrada sin visita `active`.
    Las visitas para llevar no tienen mesa y no cuentan. La suma de las tres es el numero de mesas activas.
    """
    # Un borrador SIN partidas (el lugar de un comensal que aun no pide nada) se IGNORA: ni retiene la mesa ni
    # cuenta como orden. Un borrador con partidas si es una cuenta en curso.
    borrador_vacio = and_(
        RestaurantOrder.status == ESTATUS_BORRADOR,
        ~exists(select(RestaurantOrderItem.id_restaurant_order_item).where(
            RestaurantOrderItem.id_restaurant_order == RestaurantOrder.id_restaurant_order)),
    )
    ordenes_vivas = (
        RestaurantOrder.id_restaurant_visit == RestaurantVisit.id_restaurant_visit,
        RestaurantOrder.deletion_date.is_(None),
        ~borrador_vacio,
    )
    con_ordenes = exists(select(RestaurantOrder.id_restaurant_order).where(*ordenes_vivas))
    sin_pagar = exists(select(RestaurantOrder.id_restaurant_order).where(*ordenes_vivas, RestaurantOrder.status != ESTADO_DE_VENTA))
    categoria = case((con_ordenes & ~sin_pagar, MESA_POR_LIBERAR), else_=MESA_CON_CUENTA_PENDIENTE)
    mesas_activas = _por_proyecto(
        [RestaurantTable.deletion_date.is_(None), RestaurantTable.is_active.is_(True)],
        RestaurantTable.id_proyect, actor_project,
    )
    ocupadas = (
        select(categoria, func.count(func.distinct(RestaurantTable.id_restaurant_table)))
        .select_from(RestaurantVisit)
        .join(RestaurantTable, RestaurantTable.id_restaurant_table == RestaurantVisit.id_restaurant_table)
        .where(*mesas_activas, RestaurantVisit.status == "active", RestaurantVisit.deletion_date.is_(None))
        .group_by(categoria)
    )
    conteos = {cat: int(n) for cat, n in session.execute(ocupadas).all()}
    total = int(session.scalar(select(func.count(RestaurantTable.id_restaurant_table)).where(*mesas_activas)) or 0)
    conteos[MESA_LIBRE] = total - conteos.get(MESA_CON_CUENTA_PENDIENTE, 0) - conteos.get(MESA_POR_LIBERAR, 0)
    return [(cat, fecha_fin, conteos.get(cat, 0)) for cat in MESAS_CATEGORIAS]


def definiciones():
    from app.kpis.registry import KpiDefinition

    return (
        KpiDefinition(
            clave="ventas_restaurante",
            etiqueta="Ventas del restaurante",
            modulo="restaurante",
            dimensiones=("global",),
            query_builder=ventas_restaurante_query,
            agregacion="suma",
            unidad="moneda",
            direccion="alto_es_mejor",
            graficas_permitidas=("numero", "barras", "linea", "area"),
            grafica_default="linea",
            descripcion="Subtotal de las órdenes cobradas (sin propina), por día de cobro.",
        ),
        KpiDefinition(
            clave="ventas_por_mesero",
            etiqueta="Ventas por mesero",
            modulo="restaurante",
            dimensiones=("mesero",),
            query_builder=ventas_por_mesero_query,
            agregacion="suma",
            unidad="moneda",
            sin_asignar=True,
            direccion="alto_es_mejor",
            graficas_permitidas=("barras", "dona", "numero"),
            grafica_default="barras",
            descripcion="Subtotal de las órdenes cobradas (sin propina), por mesero y por día de cobro.",
        ),
        KpiDefinition(
            clave="ticket_promedio",
            etiqueta="Ticket promedio",
            modulo="restaurante",
            dimensiones=("global",),
            query_builder=ticket_promedio_query,
            agregacion="promedio_ponderado",
            unidad="moneda",
            direccion="alto_es_mejor",
            graficas_permitidas=("numero", "barras", "linea", "area"),
            grafica_default="numero",
            descripcion="Subtotal vendido entre el número de órdenes cobradas.",
        ),
        KpiDefinition(
            clave="propinas_restaurante",
            etiqueta="Propinas del restaurante",
            modulo="restaurante",
            dimensiones=("global",),
            query_builder=propinas_restaurante_query,
            agregacion="suma",
            unidad="moneda",
            direccion="neutral",
            graficas_permitidas=("numero", "barras", "linea", "area"),
            grafica_default="numero",
            descripcion="Propinas de las órdenes cobradas, por día de cobro. Se reparten entre todos: no hay versión por mesero.",
        ),
        KpiDefinition(
            clave="propina_pct_de_venta",
            etiqueta="Propina como % de la venta",
            modulo="restaurante",
            dimensiones=("global",),
            query_builder=propina_pct_de_venta_query,
            agregacion="promedio_ponderado",
            unidad="porcentaje",
            direccion="alto_es_mejor",
            graficas_permitidas=("numero", "barras", "linea", "area"),
            grafica_default="numero",
            descripcion="Propinas entre el subtotal vendido, de las órdenes cobradas.",
        ),
        KpiDefinition(
            clave="platillos_mas_vendidos",
            etiqueta="Platillos más vendidos",
            modulo="restaurante",
            dimensiones=("platillo",),
            query_builder=platillos_mas_vendidos_query,
            agregacion="suma",
            unidad="numero",
            sin_asignar=True,
            direccion="alto_es_mejor",
            graficas_permitidas=("barras", "dona"),
            grafica_default="barras",
            limite_categorias=10,
            descripcion="Cantidad vendida de cada platillo en las órdenes cobradas: los 10 más vendidos.",
        ),
        KpiDefinition(
            clave="frecuencia_por_platillo",
            etiqueta="Frecuencia por platillo",
            modulo="restaurante",
            dimensiones=("platillo",),
            query_builder=frecuencia_por_platillo_query,
            agregacion="suma",
            unidad="numero",
            sin_asignar=True,
            direccion="alto_es_mejor",
            graficas_permitidas=("barras", "dona"),
            grafica_default="barras",
            limite_categorias=10,
            descripcion="En cuántas órdenes cobradas distintas aparece cada platillo: los 10 más frecuentes.",
        ),
        KpiDefinition(
            clave="top_mesas",
            etiqueta="Mesas con más venta",
            modulo="restaurante",
            dimensiones=("mesa",),
            query_builder=top_mesas_query,
            agregacion="suma",
            unidad="moneda",
            sin_asignar=True,
            direccion="alto_es_mejor",
            graficas_permitidas=("barras", "dona"),
            grafica_default="barras",
            limite_categorias=10,
            descripcion="Subtotal vendido por mesa (sin servicio para llevar): las 10 con más venta.",
        ),
        KpiDefinition(
            clave="servicios_por_mesero",
            etiqueta="Servicios por mesero",
            modulo="restaurante",
            dimensiones=("mesero",),
            query_builder=servicios_por_mesero_query,
            agregacion="suma",
            unidad="numero",
            sin_asignar=True,
            direccion="alto_es_mejor",
            graficas_permitidas=("barras", "dona", "numero"),
            grafica_default="barras",
            descripcion="Órdenes enviadas a cocina por mesero, por día de envío.",
        ),
        KpiDefinition(
            clave="tiempo_de_entrega",
            etiqueta="Tiempo de entrega",
            modulo="restaurante",
            dimensiones=("global",),
            query_builder=tiempo_de_entrega_query,
            agregacion="promedio_ponderado",
            unidad="minutos",
            direccion="bajo_es_mejor",
            graficas_permitidas=("numero", "barras", "linea", "area"),
            grafica_default="linea",
            descripcion=(
                "Minutos promedio entre «lista para entrega» y «entregado», por orden. Cuenta toda orden "
                "entregada, cobrada o no (vista en vivo para el gerente)."
            ),
        ),
        KpiDefinition(
            clave="diferencia_de_caja",
            etiqueta="Desviación de caja",
            modulo="restaurante",
            dimensiones=("empleado",),
            etiqueta_dimension="Cajero",
            query_builder=diferencia_de_caja_query,
            agregacion="suma",
            unidad="moneda",
            sin_asignar=True,
            direccion="bajo_es_mejor",
            graficas_permitidas=("barras", "numero"),
            grafica_default="barras",
            descripcion=(
                "Suma del valor absoluto de la diferencia de cada sesión de caja cerrada (sobrante y faltante "
                "pesan igual y no se compensan), por cajero y día de cierre."
            ),
        ),
        KpiDefinition(
            clave="pedidos_del_dia",
            etiqueta="Pedidos del día",
            modulo="restaurante",
            dimensiones=("estado",),
            etiqueta_dimension="Estado del pedido",
            query_builder=pedidos_del_dia_query,
            agregacion="ultimo",
            unidad="numero",
            direccion="neutral",
            graficas_permitidas=("dona", "barras"),
            grafica_default="dona",
            colores_categoria=PEDIDOS_COLORES,
            orden_categorias=PEDIDOS_CATEGORIAS,
            descripcion=(
                "Foto de hoy: pedidos hechos (sin borradores) cobrados, entregados sin cobrar y en curso "
                "(pedido, en preparación, lista para entrega). La suma es el total de pedidos hechos hoy."
            ),
        ),
        KpiDefinition(
            clave="cuentas_sin_cobrar",
            etiqueta="Cuentas sin cobrar",
            modulo="restaurante",
            dimensiones=("global",),
            query_builder=cuentas_sin_cobrar_query,
            agregacion="ultimo",
            unidad="moneda",
            direccion="neutral",
            graficas_permitidas=("numero", "barras", "linea"),
            grafica_default="numero",
            descripcion=(
                "Foto de hoy: monto (sin propina) de las órdenes entregadas que aún no se cobran, de cualquier día. "
                "Explica una desviación de caja: es consumo ya entregado que todavía no entra a la caja."
            ),
        ),
        KpiDefinition(
            clave="mesas_ocupadas",
            etiqueta="Mesas ocupadas",
            modulo="restaurante",
            dimensiones=("estado",),
            etiqueta_dimension="Estado de la mesa",
            query_builder=mesas_ocupadas_query,
            agregacion="ultimo",
            unidad="numero",
            direccion="neutral",
            graficas_permitidas=("dona", "barras"),
            grafica_default="dona",
            colores_categoria=MESAS_COLORES,
            orden_categorias=MESAS_CATEGORIAS,
            etiquetas_categoria=MESAS_ETIQUETAS,
            descripcion=(
                "Foto de hoy: mesas libres, ocupadas con cuenta pendiente y «Pagada, aún ocupada» (visita activa con al "
                "menos una orden y todas pagadas). La mesa se libera cuando el mesero cierra la visita, no al cobrar: si "
                "el mesero no la cierra, seguirá apareciendo como «Pagada, aún ocupada»."
            ),
        ),
    )
