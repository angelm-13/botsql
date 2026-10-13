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
"""

from __future__ import annotations

from sqlalchemy import func, select

from app.models.restaurant import RestaurantOrder, RestaurantOrderItem

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
