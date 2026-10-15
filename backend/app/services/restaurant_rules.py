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
* El dia de un KPI es el DIA OPERATIVO (`dia_operativo`): el de la apertura de la sesion de caja
  que estaba abierta en ese instante. Un turno que cierra pasada la medianoche cuenta completo en
  el dia en que abrio. Sin ninguna sesion que lo contenga, es el dia calendario del negocio.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import case, exists, func, or_, select
from sqlalchemy.orm import aliased

from app.models.restaurant import RestaurantCashSession, RestaurantOrder, RestaurantOrderItem
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
