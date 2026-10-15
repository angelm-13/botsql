"""Reglas del restaurante que comparten el servicio y los KPIs.

Por que existe
--------------
"Que cuenta como una venta del restaurante" lo usaban el corte de caja, los
KPIs en vivo del servicio y el reporte de ventas, cada uno con su propia
comparacion contra la cadena `"pagado"`. Los KPIs del Dashboard
(`app/kpis/modulos/restaurante.py`) son una cuarta lectura de lo mismo: si la
regla cambia, tiene que cambiar en UN lugar.

La regla
--------
* Una orden es venta cuando su estatus es `pagado` y no esta borrada. Un
  `borrador`, un `pedido` o un `entregado` todavia no se cobraron.
* El dia de la venta es el de `paid_at`, no el de la visita ni el de captura.
* El importe de un renglon es `cantidad x precio unitario`. No es una columna:
  el subtotal de la orden es una propiedad de Python
  (`RestaurantOrder.subtotal`) que suma `RestaurantOrderItem.line_total`. Aqui
  esta la misma cuenta para que se pueda escribir en SQL.
* La venta es el SUBTOTAL: no incluye la propina (`tip_amount`), igual que
  Facturacion mide `subtotal` y no `total`. La propina es de la ORDEN y se reparte entre todo el
  personal: no se atribuye a un mesero.
* Un "servicio" es una orden enviada a cocina (`sent_at` no nulo), cobrada o no.
* Los calculos de abajo (`ordenes_cobradas`, `renglones_vendidos`, `entregas`, `mesas_por_estado`,
  `servicios_por_mesa`) los usan LOS DOS lectores: los KPIs del Dashboard (por dia operativo) y las
  tarjetas de "Administracion del restaurante" (`RestaurantService.kpis()`, acumulado: sin fechas).
  Cada uno es una consulta agregada en SQL; ninguna carga ordenes a memoria.
* El dia de un KPI es el DIA OPERATIVO (`dia_operativo`): el de la apertura de la sesion de caja
  que estaba abierta en ese instante. Un turno que cierra pasada la medianoche cuenta completo en
  el dia en que abrio. Sin ninguna sesion que lo contenga, es el dia calendario del negocio.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, case, exists, func, or_, select
from sqlalchemy.orm import aliased

from app.models.restaurant import (
    RestaurantCashSession, RestaurantOrder, RestaurantOrderItem, RestaurantTable, RestaurantVisit,
)
from app.utils.tiempo import dia_local, mayor_de, menor_de, rango_utc_de_dias

# Cota superior de "sin cierre": una sesion que sigue abierta no tiene tope.
SIN_TOPE = datetime(9999, 12, 31)

# La unica definicion del estatus de una orden cobrada.
ESTADO_DE_VENTA = "pagado"


def condiciones_de_venta() -> tuple:
    """Condiciones SQL para quedarse solo con las ordenes que son venta."""
    return (
        RestaurantOrder.status == ESTADO_DE_VENTA,
        RestaurantOrder.deletion_date.is_(None),
    )


def importe_de_renglon():
    """Expresion SQL del importe de un renglon (`RestaurantOrderItem.line_total`)."""
    return RestaurantOrderItem.quantity * RestaurantOrderItem.unit_price


def subtotal_por_orden():
    """Subconsulta `{id_restaurant_order, subtotal}`: lo que `RestaurantOrder.subtotal` calcula en Python.

    Se une con `OUTER JOIN` y se lee con `coalesce(subtotal, 0)`: una orden cobrada sin renglones
    existe (vale 0) y cuenta como orden, igual que en el ticket promedio del servicio, que divide
    entre TODAS las ordenes cobradas.
    """
    return (
        select(
            RestaurantOrderItem.id_restaurant_order.label("id_restaurant_order"),
            func.sum(importe_de_renglon()).label("subtotal"),
        )
        .group_by(RestaurantOrderItem.id_restaurant_order)
        .subquery()
    )


def dia_operativo(columna, id_proyect=None):
    """Expresion SQL: el dia operativo (fecha LOCAL del negocio) de un instante guardado en UTC.

    Es la fecha local (`dia_local`) de `opened_at` de la sesion de caja del proyecto que contiene
    el instante `columna` (`opened_at <= columna` y sin cerrar o `closed_at >= columna`). Si ninguna
    lo contiene -un cobro con tarjeta o transferencia con la caja cerrada- cae a la fecha calendario
    local del propio instante.

    * No hay columna ni migracion: ni la orden ni el cobro guardan la sesion; se vincula por tiempo y
      proyecto, igual que `RestaurantService.close_cash_session` (`paid_at >= opened_at`). Solo hay una
      sesion abierta por proyecto, asi que las sesiones no se traslapan y `max(opened_at)` es la unica.
    * `id_proyect`: columna del proyecto de la fila que se fecha; por omision el de la orden.
    * Se escribe con `max(...)` y no con `ORDER BY ... LIMIT 1` a proposito: un LIMIT lleva parametro
      y PostgreSQL ya no reconoce la subconsulta del SELECT como la misma del GROUP BY.
    """
    if id_proyect is None:
        id_proyect = RestaurantOrder.id_proyect
    sesion = aliased(RestaurantCashSession)
    apertura = (
        select(dia_local(func.max(sesion.opened_at)))
        .where(
            sesion.id_proyect == id_proyect,
            sesion.deletion_date.is_(None),
            sesion.opened_at <= columna,
            or_(sesion.closed_at.is_(None), sesion.closed_at >= columna),
        )
        .scalar_subquery()
    )
    return func.coalesce(apertura, dia_local(columna))


def en_dias_operativos(columna, fecha_inicio, fecha_fin, actor_project=None) -> list:
    """Condiciones SQL: el dia operativo de `columna` esta entre `fecha_inicio` y `fecha_fin` (incluidos).

    Equivale a `dia_operativo(columna) BETWEEN inicio AND fin`, mas una ventana de tiempo gruesa sobre
    la columna cruda. La ventana es solo para el rendimiento: sin ella la subconsulta de `dia_operativo`
    se evalua en CADA orden del proyecto (medido: 8.9 s para un ano de 200 mil ordenes, 3.1 s para
    un solo dia) y con ella solo en las del rango. No cambia el resultado: es un superconjunto exacto.

    Un instante con dia operativo en el rango esta (a) dentro de una sesion que abrio en el rango, o (b)
    sin sesion, en un dia calendario local del rango. Por eso la ventana va desde lo MAS TEMPRANO entre el
    inicio del primer dia local y la apertura de la primera sesion del rango, hasta lo MAS TARDE entre el
    fin del ultimo dia local y el cierre de la ultima sesion del rango (sin tope si alguna sigue abierta).
    """
    inicio_utc, fin_utc = rango_utc_de_dias(fecha_inicio, fecha_fin)
    sesion = aliased(RestaurantCashSession)

    def sesiones_del_rango(*columnas):
        # Sin correlacion con la fila: se evalua UNA vez por consulta. Con `actor_project` solo las de ese
        # restaurante; sin el, las de todos (una ventana mas ancha, nunca mas angosta).
        consulta = select(*columnas).where(
            sesion.deletion_date.is_(None),
            dia_local(sesion.opened_at) >= fecha_inicio,
            dia_local(sesion.opened_at) <= fecha_fin,
        )
        return consulta.where(sesion.id_proyect == actor_project) if actor_project is not None else consulta

    primera_apertura = sesiones_del_rango(func.min(sesion.opened_at)).scalar_subquery()
    ultimo_cierre = sesiones_del_rango(func.max(sesion.closed_at)).scalar_subquery()
    alguna_abierta = exists(sesiones_del_rango(sesion.id_restaurant_cash_session).where(sesion.closed_at.is_(None)))
    # Dos cotas simples (no un OR de rangos): asi PostgreSQL las usa como rango de indice, con las subconsultas
    # sin correlacion evaluadas una sola vez. `<=` incluye de mas el instante exacto de `fin_utc`: es un
    # superconjunto, el filtro por dia operativo de abajo es el exacto.
    desde = menor_de(inicio_utc, func.coalesce(primera_apertura, inicio_utc))
    hasta = mayor_de(fin_utc, func.coalesce(case((alguna_abierta, SIN_TOPE), else_=ultimo_cierre), fin_utc))
    dia = dia_operativo(columna)
    return [columna >= desde, columna <= hasta, dia >= fecha_inicio, dia <= fecha_fin]


# --- calculos compartidos entre los KPIs del Dashboard y las tarjetas del restaurante ---------
#
# Todos reciben `fecha_inicio`/`fecha_fin` (dia operativo, ambos incluidos) o `None, None` para el ACUMULADO
# de siempre -las tarjetas-, y `actor_project` (`None` = todos los restaurantes). Con `por_dia=True` regresan una
# fila por dia operativo; con `por_dia=False`, una sola fila sin fecha.

ESTATUS_BORRADOR = "borrador"

MESA_LIBRE = "libre"
MESA_CON_CUENTA_PENDIENTE = "ocupada_con_cuenta_pendiente"
MESA_POR_LIBERAR = "por_liberar"
MESAS_CATEGORIAS = (MESA_LIBRE, MESA_CON_CUENTA_PENDIENTE, MESA_POR_LIBERAR)


def por_proyecto(condiciones: list, columna, actor_project) -> list:
    """Agrega `columna == actor_project` a `condiciones` si hay proyecto (la regla de alcance de todo `restaurant_*`)."""
    if actor_project is not None:
        condiciones.append(columna == actor_project)
    return condiciones


def _rango_de_ventas(fecha_inicio, fecha_fin, actor_project) -> list:
    if fecha_inicio is None and fecha_fin is None:
        return []
    return en_dias_operativos(RestaurantOrder.paid_at, fecha_inicio, fecha_fin, actor_project)


def renglones_vendidos(session, fecha_inicio, fecha_fin, actor_project, columnas_de_grupo, agregado, *,
                       visita=False, por_dia=True):
    """`agregado` sobre los renglones de las ordenes cobradas, por `columnas_de_grupo` (y por dia operativo de cobro)."""
    condiciones = por_proyecto(
        [*condiciones_de_venta(), *_rango_de_ventas(fecha_inicio, fecha_fin, actor_project)],
        RestaurantOrder.id_proyect, actor_project,
    )
    fecha_col = dia_operativo(RestaurantOrder.paid_at)
    grupo = (*columnas_de_grupo, fecha_col) if por_dia else tuple(columnas_de_grupo)
    columnas = (*columnas_de_grupo, fecha_col.label("fecha")) if por_dia else tuple(columnas_de_grupo)
    stmt = (
        select(*columnas, agregado)
        .select_from(RestaurantOrderItem)
        .join(RestaurantOrder, RestaurantOrder.id_restaurant_order == RestaurantOrderItem.id_restaurant_order)
    )
    if visita:
        stmt = stmt.join(RestaurantVisit, RestaurantVisit.id_restaurant_visit == RestaurantOrder.id_restaurant_visit)
    stmt = stmt.where(*condiciones)
    if grupo:
        stmt = stmt.group_by(*grupo).order_by(*grupo)
    return session.execute(stmt).all()


def ordenes_cobradas(session, fecha_inicio, fecha_fin, actor_project, *, por_dia=True):
    """`(fecha, subtotal de las ordenes, propinas, numero de ordenes)` por dia operativo de cobro.

    Con `por_dia=False`, `(subtotal, propinas, ordenes)` del acumulado. Una orden cobrada sin renglones cuenta como
    orden (subtotal 0): el ticket promedio divide entre TODAS las cobradas.
    """
    sub = subtotal_por_orden()
    condiciones = por_proyecto(
        [*condiciones_de_venta(), *_rango_de_ventas(fecha_inicio, fecha_fin, actor_project)],
        RestaurantOrder.id_proyect, actor_project,
    )
    fecha_col = dia_operativo(RestaurantOrder.paid_at)
    medidas = (
        func.coalesce(func.sum(func.coalesce(sub.c.subtotal, 0)), 0),
        func.coalesce(func.sum(RestaurantOrder.tip_amount), 0),
        func.count(RestaurantOrder.id_restaurant_order),
    )
    stmt = (
        select(*((fecha_col.label("fecha"),) if por_dia else ()), *medidas)
        .select_from(RestaurantOrder)
        .outerjoin(sub, sub.c.id_restaurant_order == RestaurantOrder.id_restaurant_order)
        .where(*condiciones)
    )
    if por_dia:
        stmt = stmt.group_by(fecha_col).order_by(fecha_col)
        return session.execute(stmt).all()
    return session.execute(stmt).one()


def entregas(session, fecha_inicio, fecha_fin, actor_project, *, por_dia=True):
    """`(fecha, minutos promedio de ready_at a delivered_at, ordenes)` por dia operativo de entrega.

    Cuenta TODA orden entregada con ambas marcas, se haya cobrado o no. Con `por_dia=False`,
    `(promedio, ordenes)` del acumulado; el promedio es `None` si no hay ninguna.
    """
    fecha_col = dia_operativo(RestaurantOrder.delivered_at)
    minutos = func.extract("epoch", RestaurantOrder.delivered_at - RestaurantOrder.ready_at) / 60.0
    rango = (
        [] if fecha_inicio is None and fecha_fin is None
        else en_dias_operativos(RestaurantOrder.delivered_at, fecha_inicio, fecha_fin, actor_project)
    )
    condiciones = por_proyecto(
        [
            RestaurantOrder.deletion_date.is_(None),
            RestaurantOrder.ready_at.isnot(None),
            RestaurantOrder.delivered_at.isnot(None),
            *rango,
        ],
        RestaurantOrder.id_proyect, actor_project,
    )
    medidas = (func.avg(minutos), func.count(RestaurantOrder.id_restaurant_order))
    stmt = select(*((fecha_col.label("fecha"),) if por_dia else ()), *medidas).where(*condiciones)
    if por_dia:
        stmt = stmt.group_by(fecha_col).order_by(fecha_col)
        return session.execute(stmt).all()
    return session.execute(stmt).one()


def mesas_por_estado(session, actor_project) -> dict:
    """Mesas activas AHORA por estado: `libre`, `ocupada_con_cuenta_pendiente` y `por_liberar`.

    Una mesa se libera cuando el mesero CIERRA la visita (`RestaurantService.close_visit`), NO al cobrar:
    `pay_order` y `pay_visit` solo marcan la orden `pagado` y la visita sigue `active` hasta que alguien la
    cierra. Las categorias no se traslapan:
    * `por_liberar` ("Pagada, aun ocupada"): visita `active` con al menos UNA orden (no borrada, y sin contar
      borradores vacios) y TODAS pagadas.
    * `ocupada_con_cuenta_pendiente`: el resto de las visitas `active`: alguna orden sin pagar, o ninguna
      orden todavia (recien sentados). Un `borrador` sin partidas se IGNORA.
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
    mesas_activas = por_proyecto(
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
    return {cat: conteos.get(cat, 0) for cat in MESAS_CATEGORIAS}


def servicios_por_mesa(session, actor_project):
    """`(numero de mesa, ordenes cobradas)` por mesa, acumulado. Las de para llevar (sin mesa) no cuentan."""
    condiciones = por_proyecto([*condiciones_de_venta()], RestaurantOrder.id_proyect, actor_project)
    stmt = (
        select(RestaurantTable.number, func.count(RestaurantOrder.id_restaurant_order))
        .select_from(RestaurantOrder)
        .join(RestaurantVisit, RestaurantVisit.id_restaurant_visit == RestaurantOrder.id_restaurant_visit)
        .join(RestaurantTable, RestaurantTable.id_restaurant_table == RestaurantVisit.id_restaurant_table)
        .where(*condiciones)
        .group_by(RestaurantTable.number)
    )
    return session.execute(stmt).all()
