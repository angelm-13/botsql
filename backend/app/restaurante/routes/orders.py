from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity
from app.extensions import db
from app.restaurante.models import Dish, Guisado, Order, OrderItem, Visit, User
from app.restaurante.utils.pagination import paginate
from app.restaurante.utils.security import roles_required
from app.restaurante.utils.errors import ApiError
from app.restaurante.utils.cash import require_open_register
from app.restaurante.utils.audit import log_action
from app.restaurante.utils.rate_limit import rate_limited

"""
Rutas de ordenes: el ciclo de vida completo de la orden de UN comensal
dentro de una visita/mesa (agregar/quitar platillos, enviar a cocina,
avanzar de estatus, y cobrar).

Flujo de estatus (ver VALID_STATUSES): borrador -> pedido -> en_preparacion
-> listo_para_entrega -> entregado -> pagado.

Desde el arreglo de "reapertura completa", cada PLATILLO (OrderItem) avanza
por cocina/entregas de forma independiente: tiene su propio status y sus
propios timestamps (sent_at/cooked_at/ready_at/delivered_at). El status de
la ORDEN (Order.status) es un "rollup" calculado por _recompute_order_status:
siempre refleja el estatus MENOS avanzado entre sus platillos ya enviados
(borrador no cuenta), asi que la orden solo se considera "entregada" cuando
TODOS sus platillos ya se entregaron. Esto es lo que permite que agregar un
platillo nuevo a una orden ya servida solo afecte a ese platillo nuevo -- los
que ya se entregaron se quedan como estaban, en vez de regresar todos juntos
a "pedido" como pasaba antes.

Autorizacion por ROL, no por "dueno" de la orden/mesa (decision de negocio
intencional, no un descuido): cualquier mesero autenticado puede agregar
platillos, enviar a cocina o marcar el estatus de la orden de CUALQUIER
mesa, sin importar que mesero la haya abierto originalmente. Un piso de
restaurante real funciona asi -- un mesero cubre a un companero en su
descanso, dos meseros atienden la misma mesa grande en hora pico, etc.
Restringir por "solo el mesero que abrio la mesa puede tocarla" romperia
ese flujo normal de un restaurante compartido. Waiter.id que ya se guarda
en cada Order (ver create_visit/add_diner en visits.py) es solo para
atribuir el KPI de "servicios por mesero" en los reportes, NUNCA se usa
para restringir acceso.
"""

orders_bp = Blueprint('orders', __name__)

VALID_STATUSES = ['borrador', 'pedido', 'en_preparacion', 'listo_para_entrega', 'entregado', 'pagado']
VALID_ITEM_STATUSES = ['pedido', 'en_preparacion', 'listo_para_entrega', 'entregado']
VALID_PAYMENT_METHODS = ['efectivo', 'tarjeta', 'transferencia', 'mixto']
IVA_RATE = 0.16  # IVA fijo de Mexico, aplicado solo si el cajero marca "aplicar IVA" al cobrar.

STAGE_ORDER = ['borrador', 'pedido', 'en_preparacion', 'listo_para_entrega', 'entregado']
STAGE_INDEX = {s: i for i, s in enumerate(STAGE_ORDER)}

# Un platillo se puede cancelar mientras no haya llegado a "listo para
# entrega": ya en esa etapa esta fisicamente terminado y a punto de
# servirse, asi que cancelarlo desde aqui ya no tiene sentido operativo.
CANCELLABLE_ITEM_STATUSES = ('borrador', 'pedido', 'en_preparacion')


def _ensure_visit_active(order):
    """Bloquea cualquier mutacion sobre una orden cuya Visit padre ya se
    cerro. Sin esto, una orden 'cancelado' (todos sus platillos cancelados)
    sobrevive a close_visit() -no se borra, solo las 'borrador' vacias se
    borran- y queda viva con status en ('borrador','cancelado'), que es
    justo lo que add_item() acepta como "reanudar esta orden": cualquiera
    podia reabrir silenciosamente la orden de una mesa ya cerrada y
    liberada para el siguiente servicio, mezclando datos de dos visitas."""
    if order.visit and order.visit.status != 'active':
        raise ApiError('Esta mesa/visita ya esta cerrada', 409, 'visit_closed')


def _recompute_order_status(order):
    """Recalcula Order.status a partir del estatus de sus platillos.

    La orden queda en la etapa MENOS avanzada entre sus platillos que ya se
    enviaron a cocina (los que siguen en 'borrador' -sin enviar todavia- no
    cuentan). Asi, si una orden ya entregada recibe un platillo nuevo, la
    orden completa vuelve a mostrarse como 'pedido' (hay algo pendiente por
    servir) SIN tocar el status individual de los platillos que ya se
    sirvieron -- esos se quedan en 'entregado' y no vuelven a aparecer en
    los tableros de cocina/entregas.

    Los timestamps de la orden (sent_at/cooked_at/ready_at/delivered_at) se
    llenan una sola vez, la primera vez que TODOS los platillos enviados
    alcanzan esa etapa, y ya no se vuelven a borrar despues (para no alterar
    los KPIs de tiempos de servicio ya calculados sobre esa primera vez).

    Devuelve True si el estatus de la orden retrocedio respecto al que tenia
    antes de esta llamada (por ejemplo de 'entregado' a 'pedido'), para que
    el mesero reciba un aviso claro de que se reabrio hacia cocina.

    Caso especial -- reordenar tras cancelar todo: si TODOS los platillos
    que se habian enviado terminaron cancelados, la orden queda 'cancelado'
    (ver mas abajo) y el mesero tiene dos caminos: cerrar la mesa (ya no
    cuenta como "orden sin pagar" para close_visit, ver visits.py), o pedir
    algo mas. Si eligen pedir algo mas, add_item() hace nacer ese platillo
    nuevo en 'borrador' (igual que una orden nunca antes enviada, en vez de
    mandarlo directo a cocina) -- y aqui, mientras exista CUALQUIER platillo
    en 'borrador' (una ronda nueva que el mesero todavia esta armando), la
    orden se muestra como 'borrador' para que aparezca el boton normal de
    "Enviar a cocina", sin importar que haya platillos cancelados en su
    historial. Sin esto, la orden se quedaria trabada en 'cancelado' para
    siempre y el platillo nuevo nunca se enviaria explicitamente.
    """
    previous_status = order.status
    drafting = [it for it in order.items if it.status in (None, 'borrador')]
    # "real_items": platillos que en algun momento se enviaron a cocina
    # (excluye los que siguen en borrador/sin enviar). "sendable": de esos,
    # los que NO estan cancelados -- son los unicos que cuentan para saber
    # que tan avanzada va la orden.
    real_items = [it for it in order.items if it.status and it.status != 'borrador']
    sendable = [it for it in real_items if it.status != 'cancelado']
    if not sendable:
        if drafting:
            order.status = 'borrador'
        elif real_items:
            # Se enviaron platillos alguna vez y TODOS terminaron cancelados,
            # sin ninguna ronda nueva en borrador todavia: la orden en
            # conjunto se marca 'cancelado' (no 'borrador': ya se le mando
            # algo a cocina, no es un borrador sin tocar).
            order.status = 'cancelado'
        else:
            order.status = 'borrador'
        return False
    order.status = STAGE_ORDER[min(STAGE_INDEX[it.status] for it in sendable)]
    now = datetime.utcnow()
    if not order.sent_at:
        order.sent_at = min((it.sent_at for it in sendable if it.sent_at), default=now)
    if not order.cooked_at and all(STAGE_INDEX[it.status] >= STAGE_INDEX['en_preparacion'] for it in sendable):
        order.cooked_at = max((it.cooked_at for it in sendable if it.cooked_at), default=now)
    if not order.ready_at and all(STAGE_INDEX[it.status] >= STAGE_INDEX['listo_para_entrega'] for it in sendable):
        order.ready_at = max((it.ready_at for it in sendable if it.ready_at), default=now)
    if not order.delivered_at and all(it.status == 'entregado' for it in sendable):
        order.delivered_at = max((it.delivered_at for it in sendable if it.delivered_at), default=now)
    previous_idx = STAGE_INDEX.get(previous_status)
    return previous_idx is not None and STAGE_INDEX[order.status] < previous_idx


@orders_bp.get('')
@roles_required('cajero', 'admin', 'cocina', 'mesero', 'superadmin')
def list_orders():
    """Lista ordenes con filtros opcionales por status/visita/mesero (usado por los tableros y por cajero para ver cuentas por cobrar)."""
    q = Order.query
    status = request.args.get('status')
    visit_id = request.args.get('visit_id')
    waiter_id = request.args.get('waiter_id')
    if status:
        q = q.filter(Order.status == status)
    if visit_id:
        q = q.filter(Order.visit_id == int(visit_id))
    if waiter_id:
        q = q.filter(Order.waiter_id == int(waiter_id))
    return jsonify(paginate(q.order_by(Order.started_at.desc()), request))


@orders_bp.get('/<int:order_id>')
@roles_required('cajero', 'admin', 'cocina', 'mesero', 'superadmin')
def get_order(order_id):
    """Devuelve el detalle completo de una orden (items, guisados, tiempos, montos)."""
    order = Order.query.get_or_404(order_id)
    return jsonify(order.to_dict())


@orders_bp.post('/<int:order_id>/items')
@roles_required('mesero', 'cajero')
def add_item(order_id):
    """Agrega un platillo a la orden (mientras no este pagada). Valida que el platillo exista, este activo, y que traiga guisado si el platillo lo requiere."""
    order = Order.query.get_or_404(order_id)
    if order.status == 'pagado':
        raise ApiError('Order already paid', 409, 'order_paid')
    _ensure_visit_active(order)
    data = request.get_json() or {}
    dish = Dish.query.get(data.get('dish_id'))
    if not dish or not dish.is_active:
        raise ApiError('Dish not found', 404, 'dish_not_found')
    if dish.requires_guisado and not data.get('guisado_1_id'):
        raise ApiError('This dish requires at least one guisado', 422, 'guisado_required')

    # Antes solo se checaba que guisado_1_id/guisado_2_id vinieran presentes,
    # nunca que de verdad existieran o siguieran activos (Guisado.is_active) --
    # un id inexistente pasaba de largo esta validacion y solo tronaba hasta
    # el commit, como un 500 generico por la foreign key. Ademas, 'combinado'
    # y la cantidad de guisados nunca se cruzaban entre si: se podia guardar
    # combinado=true con un solo guisado, o combinado=false con dos.
    guisado_1_id = data.get('guisado_1_id')
    guisado_2_id = data.get('guisado_2_id')
    combinado = bool(data.get('combinado', False))
    if dish.requires_guisado:
        for gid in (guisado_1_id, guisado_2_id):
            if gid is not None:
                guisado = Guisado.query.get(gid)
                if not guisado or not guisado.is_active:
                    raise ApiError('El guisado seleccionado no existe o ya no esta disponible', 422, 'guisado_not_found')
        if combinado and not guisado_2_id:
            raise ApiError('Un platillo combinado requiere dos guisados', 422, 'validation_error')
        # BUG: esta linea forzaba guisado_2_id a None cada vez que
        # combinado=False, sin importar si de verdad venia un segundo
        # guisado -- lo cual describe EXACTAMENTE al modo "2 guisados" del
        # frontend (AddItemModal manda combinado=false junto con un
        # guisado_2_id real en ese modo, distinto de "Combinado"). Resultado:
        # el modo "2 guisados" nunca guardaba el segundo relleno elegido; la
        # orden se guardaba y se veia en cocina como si el mesero solo
        # hubiera elegido un guisado. Se quita por completo: no hay ninguna
        # razon de negocio para descartar un guisado_2_id valido cuando NO
        # es combinado, solo para el caso combinado=true SIN guisado_2 (ya
        # rechazado arriba).
        if guisado_2_id is not None and guisado_1_id is not None and str(guisado_1_id) == str(guisado_2_id):
            raise ApiError('No puedes elegir el mismo guisado dos veces', 422, 'validation_error')
    else:
        guisado_1_id, guisado_2_id, combinado = None, None, False

    now = datetime.utcnow()
    # Si la orden todavia no se ha enviado (sigue en 'borrador'), el platillo
    # nace en borrador tambien -- se ira a cocina hasta que el mesero mande
    # todo junto con /send. Lo mismo aplica si la orden quedo 'cancelado'
    # (se cancelaron TODOS los platillos que se habian enviado): el
    # siguiente platillo es un pedido nuevo desde cero, asi que el mesero
    # decide cuando mandarlo con el boton de "Enviar a cocina" -- no se
    # asume que quiere mandarlo de inmediato solo porque antes hubo algo
    # cancelado. Si la orden YA se habia enviado antes y sigue activa (esta
    # en pedido/en_preparacion/listo_para_entrega/entregado), este platillo
    # es una RONDA NUEVA e independiente: entra directo a cocina, sin tocar
    # el estatus de los platillos que ya iban en camino o que ya se sirvieron.
    if order.status in ('borrador', 'cancelado'):
        item_status, item_sent_at = 'borrador', None
    else:
        item_status, item_sent_at = 'pedido', now

    item = OrderItem(
        order_id=order.id,
        dish_id=dish.id,
        quantity=max(int(data.get('quantity', 1)), 1),
        unit_price=dish.price,
        note=(data.get('note') or '').strip()[:255] or None,
        guisado_1_id=guisado_1_id,
        guisado_2_id=guisado_2_id,
        combinado=combinado,
        status=item_status,
        sent_at=item_sent_at,
    )
    db.session.add(item)
    db.session.flush()

    reopened_for_kitchen = _recompute_order_status(order)

    db.session.commit()
    result = order.to_dict()
    result['reopened_for_kitchen'] = reopened_for_kitchen
    return jsonify(result), 201


@orders_bp.delete('/<int:order_id>/items/<int:item_id>')
@roles_required('mesero', 'cajero')
def remove_item(order_id, item_id):
    """Quita un platillo de la orden -- SOLO si nunca se envio a cocina
    (status 'borrador'/None). Antes esto solo validaba order.status !=
    'pagado', sin revisar item.status: un platillo ya enviado (incluso ya
    'entregado') se podia borrar por completo con este mismo DELETE, sin
    motivo, sin rol admin y sin quedar en la bitacora de auditoria,
    evadiendo por completo las protecciones de cancel_item (que exige
    admin + motivo, y preserva el registro como 'cancelado' en vez de
    borrarlo). Un platillo ya enviado a cocina debe cancelarse, no borrarse."""
    order = Order.query.get_or_404(order_id)
    if order.status == 'pagado':
        raise ApiError('Esta orden ya fue cobrada', 409, 'order_paid')
    item = OrderItem.query.filter_by(id=item_id, order_id=order.id).first_or_404()
    if item.status not in (None, 'borrador'):
        raise ApiError('Este platillo ya se envio a cocina; para quitarlo debe cancelarse con un motivo', 409, 'item_already_sent')
    db.session.delete(item)
    db.session.flush()
    _recompute_order_status(order)
    db.session.commit()
    return jsonify(order.to_dict())


@orders_bp.post('/<int:order_id>/send')
@roles_required('mesero', 'cajero')
def send_to_kitchen(order_id):
    """Envia la orden a cocina: cada platillo que siga en 'borrador' pasa a
    'pedido' y guarda su propio sent_at (hora real de envio); el status de
    la orden se recalcula a partir de sus platillos."""
    order = Order.query.get_or_404(order_id)
    _ensure_visit_active(order)
    if not order.items:
        raise ApiError('Add at least one dish before sending to the kitchen', 422, 'validation_error')
    now = datetime.utcnow()
    for item in order.items:
        if item.status in (None, 'borrador'):
            item.status = 'pedido'
            item.sent_at = now
    _recompute_order_status(order)
    db.session.commit()
    return jsonify(order.to_dict())


@orders_bp.patch('/<int:order_id>/status')
@roles_required('cocina', 'mesero', 'cajero')
def update_status(order_id):
    """Avanza EN BLOQUE los platillos de la orden que esten en su etapa menos
    avanzada (por ejemplo, para el boton "marcar entregado" del ticket del
    mesero, que cobra sentido cuando todos sus platillos llegaron juntos a la
    misma etapa). Los platillos que ya vayan mas adelantados, o que ya esten
    entregados, no se tocan. Para avanzar un platillo especifico de forma
    independiente, ver PATCH /<order_id>/items/<item_id>/status."""
    order = Order.query.get_or_404(order_id)
    if order.status == 'pagado':
        raise ApiError('Esta orden ya fue cobrada', 409, 'order_paid')
    data = request.get_json() or {}
    new_status = data.get('status')
    # 'pagado' es un estatus valido de Order, pero solo /pay puede asignarlo
    # (ahi se calculan montos, propina, etc.) -- STAGE_ORDER (y por lo tanto
    # STAGE_INDEX) lo excluye a proposito, asi que aceptarlo aqui haria
    # KeyError mas abajo en vez de un 422 limpio.
    if new_status not in STAGE_ORDER:
        raise ApiError('Invalid status', 422, 'invalid_status')
    now = datetime.utcnow()
    if new_status == 'pedido':
        for item in order.items:
            if item.status in (None, 'borrador'):
                item.status = 'pedido'
                item.sent_at = item.sent_at or now
    else:
        target_idx = STAGE_INDEX[new_status]
        sendable = [it for it in order.items if it.status and it.status != 'borrador']
        if sendable:
            current_min = min(STAGE_INDEX[it.status] for it in sendable)
            for it in sendable:
                if STAGE_INDEX[it.status] == current_min and current_min < target_idx:
                    it.status = new_status
                    if new_status == 'en_preparacion' and not it.cooked_at:
                        it.cooked_at = now
                    if new_status == 'listo_para_entrega' and not it.ready_at:
                        it.ready_at = now
                    if new_status == 'entregado' and not it.delivered_at:
                        it.delivered_at = now
    _recompute_order_status(order)
    db.session.commit()
    return jsonify(order.to_dict())


@orders_bp.patch('/<int:order_id>/items/<int:item_id>/status')
@roles_required('cocina', 'mesero', 'cajero')
def update_item_status(order_id, item_id):
    """Avanza el estatus de UN platillo especifico, de forma independiente del
    resto de los platillos de la misma orden -- esto es lo que usan los
    tableros de cocina y de entregas, donde cada tarjeta es un platillo y
    cada accion (aceptar/marcar listo/entregar) solo debe afectar a ese
    platillo. Al terminar, se recalcula el estatus global de la orden."""
    order = Order.query.get_or_404(order_id)
    if order.status == 'pagado':
        raise ApiError('Esta orden ya fue cobrada', 409, 'order_paid')
    # FOR UPDATE: bloquea la fila del platillo hasta el commit, para que dos
    # acciones concurrentes sobre el MISMO platillo (ej. cocina marcandolo
    # listo y admin cancelandolo casi al mismo tiempo) queden serializadas
    # en vez de que la segunda pise el resultado de la primera con datos
    # ya obsoletos (leidos antes de que la primera hiciera commit).
    item = OrderItem.query.filter_by(id=item_id, order_id=order.id).with_for_update().first_or_404()
    data = request.get_json() or {}
    new_status = data.get('status')
    if new_status not in VALID_ITEM_STATUSES:
        raise ApiError('Invalid status', 422, 'invalid_status')
    current_idx = STAGE_INDEX.get(item.status)
    target_idx = STAGE_INDEX[new_status]
    if current_idx is not None and target_idx <= current_idx:
        raise ApiError('No se puede regresar un platillo a una etapa anterior', 409, 'invalid_transition')
    item.status = new_status
    now = datetime.utcnow()
    if new_status == 'en_preparacion' and not item.cooked_at:
        item.cooked_at = now
    if new_status == 'listo_para_entrega' and not item.ready_at:
        item.ready_at = now
    if new_status == 'entregado' and not item.delivered_at:
        item.delivered_at = now
    _recompute_order_status(order)
    db.session.commit()
    return jsonify(order.to_dict())


@orders_bp.patch('/<int:order_id>/items/<int:item_id>/cancel')
@roles_required('admin', 'superadmin')
def cancel_item(order_id, item_id):
    """Cancela UN platillo especifico, en vez de borrarlo: se marca
    status='cancelado' con el motivo, quien lo cancelo y cuando (la misma
    filosofia de "nunca se borra, se marca" que usan Dish/Guisado/User).

    Exclusivo del rol admin: cancelar afecta directamente lo que se factura
    y deja de servirse, asi que se restringio a quien tiene autoridad para
    decidirlo (antes lo podian iniciar mesero/cocina/cajero tambien; se
    centralizo en admin a peticion explicita). Ver AdminOrdersPanel en el
    frontend, la unica pantalla desde la que se puede disparar esta accion.

    Solo se puede cancelar mientras el platillo siga en una etapa de
    CANCELLABLE_ITEM_STATUSES (borrador, pedido o en_preparacion); una vez
    'listo_para_entrega', 'entregado', 'pagado' o ya 'cancelado', se
    rechaza. Requiere un motivo no vacio, para dejar rastro de por que se
    cancelo (util para detectar, por ejemplo, un insumo que falta seguido).

    Al cancelar, se recalcula el rollup de la orden (_recompute_order_status):
    un platillo cancelado deja de contar para saber que tan avanzada va la
    orden, y su precio deja de sumar al subtotal (ver Order.to_dict / pay()).
    """
    order = Order.query.get_or_404(order_id)
    item = OrderItem.query.filter_by(id=item_id, order_id=order.id).first_or_404()
    if order.status == 'pagado':
        raise ApiError('Esta orden ya fue cobrada', 409, 'order_paid')
    if item.status not in CANCELLABLE_ITEM_STATUSES:
        raise ApiError('Este platillo ya no se puede cancelar en su etapa actual', 409, 'item_not_cancellable')
    data = request.get_json() or {}
    reason = (data.get('reason') or '').strip()
    if not reason:
        raise ApiError('Indica el motivo de la cancelacion', 400, 'reason_required')
    item.status = 'cancelado'
    item.cancelled_at = datetime.utcnow()
    item.cancelled_by_id = int(get_jwt_identity())
    item.cancel_reason = reason[:255]
    _recompute_order_status(order)
    log_action('order_item.cancel', 'order_item', item.id, f'Cancelo "{item.dish.title if item.dish else item.dish_id}" (orden #{order.id}). Motivo: {reason[:255]}')
    db.session.commit()
    return jsonify(order.to_dict())


@orders_bp.post('/<int:order_id>/pay')
@roles_required('cajero', 'admin', 'superadmin')
@rate_limited('order_pay', max_requests=30, window_seconds=60)
def pay(order_id):
    """Cobra una sola orden (un comensal). Requiere que la caja este abierta y
    que la orden este completamente entregada (si se agrego un platillo nuevo
    despues de servir los demas, la orden vuelve a 'pedido' hasta que ese
    platillo tambien se entregue -- no se puede cobrar algo que todavia no
    esta completo)."""
    session = require_open_register()
    # FOR UPDATE: bloquea la fila de la orden hasta el commit, para que dos
    # cobros casi simultaneos (doble clic, o retry de red) sobre la MISMA
    # orden queden serializados -- el segundo ve status=='pagado' (ya
    # escrito por el primero) y se rechaza en vez de sobreescribir en
    # silencio metodo de pago/propina/efectivo del primer cobro.
    order = Order.query.filter_by(id=order_id).with_for_update().first_or_404()
    if order.status != 'entregado':
        raise ApiError('Esta cuenta todavia tiene platillos pendientes de servir', 409, 'order_not_ready')
    data = request.get_json() or {}
    subtotal = round(float(sum([(item.quantity or 0) * float(item.unit_price or 0) for item in order.items if item.status != 'cancelado'])), 2)

    discount_amount = round(float(data.get('discount_amount', 0) or 0), 2)
    if discount_amount < 0:
        raise ApiError('El descuento no puede ser negativo', 422, 'validation_error')
    # Comparar contra el subtotal ya redondeado (no el float crudo de la
    # suma): sin este round(), un subtotal como 30.299999999999997 (error de
    # representacion binaria de 3 x $10.10) rechazaba un descuento de
    # $30.30 -exactamente el subtotal- porque 30.30 > 30.299999999999997,
    # bloqueando casos comunes como una cortesia del 100%.
    if discount_amount > subtotal:
        raise ApiError('El descuento no puede ser mayor al subtotal', 422, 'validation_error')

    apply_tax = bool(data.get('apply_tax', False))
    # El IVA se calcula sobre el subtotal YA NETO de descuento (no el bruto):
    # es la base fiscal estandar cuando hay un descuento aplicado. Antes se
    # calculaba sobre el subtotal bruto, y al facturar (build_draft_from_sale
    # en builder.py) se "reconstruia" una tasa efectiva = tax/subtotal_neto
    # para que los totales del CFDI cuadraran -- con descuento esa tasa
    # reconstruida salia distinta de 16% (ej. 17.78%), una tasa que no existe
    # en el catalogo de tasas de IVA del SAT. Calculando la base ya neta
    # aqui, la tasa reconstruida en builder.py vuelve a coincidir con
    # IVA_RATE exactamente.
    tax_amount = round((subtotal - discount_amount) * IVA_RATE, 2) if apply_tax else 0.0

    tip_type = data.get('tip_type', 'manual')
    if tip_type == 'porcentaje':
        percent = float(data.get('tip_percent', 0) or 0)
        if percent < 0:
            raise ApiError('La propina no puede ser negativa', 422, 'validation_error')
        if percent > 100:
            raise ApiError('La propina no puede ser mayor al 100%', 422, 'validation_error')
        order.tip_percent = percent
        order.tip_amount = round(subtotal * percent / 100, 2)
        order.tip_type = 'porcentaje'
    else:
        tip_amount = round(float(data.get('tip_amount', 0) or 0), 2)
        if tip_amount < 0:
            raise ApiError('La propina no puede ser negativa', 422, 'validation_error')
        order.tip_amount = tip_amount
        order.tip_type = 'manual'
        order.tip_percent = None

    payment_method = data.get('payment_method')
    if payment_method and payment_method not in VALID_PAYMENT_METHODS:
        raise ApiError('Metodo de pago invalido', 422, 'validation_error')
    order.payment_method = payment_method

    order.discount_amount = discount_amount
    order.tax_amount = tax_amount

    # Pago mixto: cash_amount es la parte del total que se cobro en efectivo
    # (el resto se asume tarjeta/transferencia). Sin esto, el corte de caja
    # no tenia forma de saber cuanto de un pago "mixto" meter al cajon.
    total = round(subtotal + float(order.tax_amount) - float(order.discount_amount) + float(order.tip_amount), 2)

    received_amount = data.get('received_amount')
    if received_amount is not None:
        received_amount = round(float(received_amount), 2)
        # Solo se valida contra el total cuando el metodo de pago en efectivo
        # aporta relevancia real al monto recibido (efectivo/mixto): antes no
        # se comparaba contra nada, asi que un cajero podia registrar un
        # cobro en efectivo por menos del total y la orden igual quedaba
        # marcada 'pagado' como si se hubiera cobrado completo.
        if payment_method in ('efectivo', 'mixto') and received_amount < total:
            raise ApiError('El monto recibido no puede ser menor al total a cobrar', 422, 'validation_error')
    order.received_amount = received_amount

    if payment_method == 'mixto':
        cash_amount = data.get('cash_amount')
        if cash_amount is None:
            raise ApiError('Falta indicar el monto en efectivo del pago mixto', 422, 'validation_error')
        cash_amount = round(float(cash_amount), 2)
        if cash_amount < 0 or cash_amount > total:
            raise ApiError('El monto en efectivo no puede ser negativo ni mayor al total', 422, 'validation_error')
        order.cash_amount = cash_amount
    else:
        order.cash_amount = None

    order.status = 'pagado'
    order.paid_at = datetime.utcnow()
    order.register_session_id = session.id
    log_action('order.pay', 'order', order.id, f'Cobro la orden #{order.id} por ${total:.2f} ({payment_method or "sin metodo"}).')
    db.session.commit()
    return jsonify(order.to_dict())


@orders_bp.post('/<int:order_id>/unpay')
@roles_required('cajero', 'admin', 'superadmin')
def unpay(order_id):
    """Corrige un cobro ya hecho: regresa la orden de 'pagado' a 'entregado' y
    limpia los campos de pago (metodo, propina, descuento, IVA, recibido),
    sin borrar ningun platillo ni su historial. Se usa cuando el cliente
    cambia de opinion sobre el metodo de pago o el cajero se equivoca al
    cobrar, para poder volver a la pantalla de pago y cobrar de nuevo bien.

    Requiere un motivo no vacio (mismo criterio que cancelar un platillo,
    ver cancel_item arriba): corregir un cobro ya hecho es sensible, y el
    motivo queda en la bitacora de auditoria (log_action)."""
    require_open_register()
    order = Order.query.get_or_404(order_id)
    if order.status != 'pagado':
        raise ApiError('Esta orden no esta pagada', 409, 'order_not_paid')
    data = request.get_json() or {}
    reason = (data.get('reason') or '').strip()
    if not reason:
        raise ApiError('Indica el motivo de la correccion', 400, 'reason_required')
    order.status = 'entregado'
    order.payment_method = None
    order.tip_type = None
    order.tip_percent = None
    order.tip_amount = 0
    order.discount_amount = 0
    order.tax_amount = 0
    order.received_amount = None
    order.cash_amount = None
    order.paid_at = None
    order.register_session_id = None
    log_action('order.unpay', 'order', order.id, f'Corrigio el cobro de la orden #{order.id}. Motivo: {reason[:255]}')
    db.session.commit()
    return jsonify(order.to_dict())


@orders_bp.get('/cancelled')
@roles_required('admin', 'superadmin')
def cancelled_items():
    """Historial de platillos cancelados (mas recientes primero), para que
    el administrador pueda auditar que se cancelo, quien lo hizo y por que.
    Exclusivo de admin, igual que la accion misma de cancelar."""
    limit = min(int(request.args.get('limit', 50)), 200)
    items = (
        OrderItem.query
        .filter(OrderItem.status == 'cancelado')
        .order_by(OrderItem.cancelled_at.desc())
        .limit(limit)
        .all()
    )
    visit_cache = {}
    user_cache = {}
    result = []
    for it in items:
        data = it.to_dict()
        order = it.order
        if order.visit_id not in visit_cache:
            visit_cache[order.visit_id] = Visit.query.get(order.visit_id)
        visit = visit_cache.get(order.visit_id)
        if it.cancelled_by_id not in user_cache:
            user = User.query.get(it.cancelled_by_id) if it.cancelled_by_id else None
            user_cache[it.cancelled_by_id] = user.username if user else None
        data['order_id'] = order.id
        data['visit_id'] = order.visit_id
        data['diner_index'] = order.diner_index
        data['table_number'] = visit.table_number if visit else None
        data['is_takeout'] = visit.is_takeout if visit else False
        data['customer_name'] = visit.customer_name if visit else None
        data['visit_daily_number'] = visit.daily_number if visit else None
        data['cancelled_by_username'] = user_cache.get(it.cancelled_by_id)
        result.append(data)
    return jsonify({'items': result})
