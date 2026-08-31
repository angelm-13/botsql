"""
Rutas de cocina.

Un solo endpoint de lectura: la lista de PLATILLOS (no ordenes completas)
que cocina todavia tiene pendientes (pedido, en preparacion o listos para
que el mesero los recoja). El tablero de cocina y el tablero de entregas
del mesero hacen polling a este mismo endpoint cada pocos segundos.

Se filtra por el estatus de CADA PLATILLO (OrderItem.status), no por el
estatus de la orden completa: asi, si una orden ya entregada recibe un
platillo nuevo, solo ese platillo nuevo aparece aqui -- los que ya se
sirvieron antes no vuelven a aparecer, aunque la orden como conjunto
momentaneamente deje de estar "entregada" (ver _recompute_order_status en
routes/orders.py).
"""
import os
from flask import Blueprint, jsonify
from app.restaurante.models import Order, OrderItem, Visit
from app.restaurante.utils.security import roles_required

kitchen_bp = Blueprint('kitchen', __name__)

ACTIVE_ITEM_STATUSES = ['pedido', 'en_preparacion', 'listo_para_entrega']
# Configurable (antes un .limit(200) fijo en el codigo): un restaurante con
# mucho volumen en hora pico puede necesitar ver mas platillos activos a la
# vez en el tablero sin tener que tocar codigo para subir el limite.
BOARD_ITEM_LIMIT = int(os.getenv('KITCHEN_BOARD_LIMIT', '200'))


@kitchen_bp.get('/board')
@roles_required('cocina', 'mesero', 'cajero', 'admin', 'superadmin')
def board():
    """Platillos activos para los tableros de cocina/entregas, del mas
    antiguo al mas nuevo. Incluye 'pedido' (recien enviado), 'en_preparacion'
    y 'listo_para_entrega' (esperando que el mesero lo recoja). No incluye
    platillos en 'borrador' (aun no enviados) ni 'entregado' (ya se sirvieron).

    No es un tablero "paginado" de verdad -- cocina/mesero necesitan ver
    TODOS los platillos activos a la vez, no navegar pagina por pagina en
    un tablero que se actualiza solo cada pocos segundos. Lo que si importa
    es que, si algun dia hay mas platillos activos que BOARD_ITEM_LIMIT, el
    tablero lo diga (`truncated`) en vez de mostrar una lista incompleta sin
    ningun aviso, como pasaba antes (pagination.total devolvia len(result),
    el numero YA recortado por el limite -- asi que "total" nunca podia
    reflejar que faltaban platillos por definicion).
    """
    base_query = (
        OrderItem.query
        .join(Order, OrderItem.order_id == Order.id)
        .filter(OrderItem.status.in_(ACTIVE_ITEM_STATUSES))
    )
    total = base_query.count()
    items = base_query.order_by(OrderItem.sent_at.asc()).limit(BOARD_ITEM_LIMIT).all()
    visit_cache = {}
    result = []
    for it in items:
        data = it.to_dict()
        order = it.order
        if order.visit_id not in visit_cache:
            visit_cache[order.visit_id] = Visit.query.get(order.visit_id)
        visit = visit_cache.get(order.visit_id)
        data['order_id'] = order.id
        data['visit_id'] = order.visit_id
        data['diner_index'] = order.diner_index
        data['table_number'] = visit.table_number if visit else None
        # Un platillo de un pedido "para llevar" no pertenece a ninguna mesa;
        # el frontend usa esta bandera (y customer_name) para mostrar
        # "Para llevar #<visit_id>" en vez de "Mesa None" en los tableros.
        data['is_takeout'] = visit.is_takeout if visit else False
        data['customer_name'] = visit.customer_name if visit else None
        # Folio del dia del pedido para llevar (ver Visit.daily_number):
        # placeLabel() en el frontend lo usa en vez de visit_id.
        data['visit_daily_number'] = visit.daily_number if visit else None
        result.append(data)
    return jsonify({
        'items': result,
        'pagination': {'page': 1, 'per_page': BOARD_ITEM_LIMIT, 'total': total, 'pages': 1, 'has_next': False, 'has_prev': False},
        'truncated': total > len(result),
    })
