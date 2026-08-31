from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt
from sqlalchemy import text
from app.extensions import db
from app.restaurante.models import Visit, Order, Table
from app.restaurante.utils.security import roles_required
from app.restaurante.utils.errors import ApiError
from app.restaurante.utils.cash import require_open_register
from app.restaurante.utils.audit import log_action

# Namespace fijo para pg_advisory_xact_lock(classid, objid) usado al abrir
# una mesa (ver create_visit): evita que dos meseros abriendo la MISMA mesa
# casi al mismo tiempo pasen ambos el chequeo de "no tiene visita activa"
# antes de que cualquiera de los dos haga commit -- el lock se libera solo
# al terminar la transaccion (commit o rollback), asi que serializa el
# chequeo-y-creacion sin necesitar una migracion de esquema nueva.
TABLE_LOCK_NAMESPACE = 918273

# Namespace fijo aparte para dos cosas que TABLE_LOCK_NAMESPACE (por numero
# de mesa) no cubre:
#   - agregar un comensal a una visita ya abierta (add_diner): dos altas
#     casi simultaneas en la MISMA mesa podian calcular el mismo
#     diner_index (no hay UniqueConstraint en el modelo) y perder un
#     incremento de diners_count (lost update).
#   - la numeracion de folios del dia (daily_number, compartida entre
#     mesas y para llevar): el lock de mesa solo serializa la apertura de
#     ESA mesa, no la lectura del COUNT() global que decide el siguiente
#     folio -- dos aperturas de mesas DISTINTAS, o una apertura de mesa a
#     la vez que un pedido para llevar, podian leer el mismo COUNT() antes
#     de comitear y terminar con dos tickets con el mismo folio el mismo
#     dia.
# Se usa una sola key fija (DAILY_NUMBER_LOCK_KEY) para serializar TODA
# asignacion de folio del dia, sin importar mesa/para-llevar/comensal
# nuevo: la seccion critica es minima (un COUNT()+1), asi que no vale la
# pena distinguir namespaces mas finos.
GLOBAL_LOCK_NAMESPACE = 918274
DAILY_NUMBER_LOCK_KEY = 1
# Namespace distinto para el lock por-visita de add_diner: pg_advisory_xact_lock
# identifica el lock por el PAR (classid, objid), asi que si comparte
# namespace con DAILY_NUMBER_LOCK_KEY, una visita con id=1 tomaria por
# accidente el mismo lock que la numeracion global de folios.
VISIT_LOCK_NAMESPACE = 918275


def _lock_daily_numbering():
    db.session.execute(text('SELECT pg_advisory_xact_lock(:ns, :key)'), {'ns': GLOBAL_LOCK_NAMESPACE, 'key': DAILY_NUMBER_LOCK_KEY})

"""
Rutas de visitas (una "visita" = una mesa abierta, desde que el mesero la
abre hasta que se cierra). Cada visita tiene una Order por comensal
(diner_index 1, 2, 3...), y aqui viven las operaciones a nivel MESA:
abrir, sumar/quitar comensales, cerrar, y el cobro conjunto de toda la
mesa (pay_visit, mas abajo).

Autorizacion por ROL, no por "dueno" de la mesa: ver la nota equivalente
al inicio de orders.py. Cualquier mesero/cajero autenticado puede abrir,
cerrar o cobrar CUALQUIER mesa -- es una decision de negocio intencional
(piso de restaurante compartido), no un hueco de autorizacion.
"""

visits_bp = Blueprint('visits', __name__)


def _tz_offset_minutes(payload):
    """Mismo criterio que _get_tz_offset_minutes en cashier.py (minutos a
    SUMAR a la hora local para obtener UTC, tal cual getTimezoneOffset())."""
    try:
        offset = int(payload.get('tz_offset_minutes', 0) or 0)
    except (TypeError, ValueError):
        offset = 0
    return max(-840, min(720, offset))


def _local_day_utc_bounds(tz_offset_minutes):
    """Rango [inicio, fin) en UTC del dia LOCAL actual del dispositivo, para
    contar cuantas visitas/ordenes ya se abrieron HOY y asignar el folio
    diario (daily_number) siguiente. Reinicia solo, un dia a la vez, sin
    guardar ningun contador aparte: el folio de la siguiente visita/orden es
    simplemente "cuantas hay ya hoy" + 1."""
    now_local = datetime.utcnow() - timedelta(minutes=tz_offset_minutes)
    start_local = datetime(now_local.year, now_local.month, now_local.day)
    start_utc = start_local + timedelta(minutes=tz_offset_minutes)
    return start_utc, start_utc + timedelta(days=1)


def _next_order_daily_number(day_start, day_end):
    return Order.query.filter(Order.started_at >= day_start, Order.started_at < day_end).count() + 1


@visits_bp.get('')
@roles_required('mesero', 'cajero', 'cocina', 'admin', 'superadmin')
def list_visits():
    """Lista visitas (mesas abiertas/cerradas o pedidos para llevar), opcionalmente
    filtradas por status y por is_takeout (para separar el listado de mesas del
    listado de pedidos para llevar en el frontend)."""
    q = Visit.query
    status = request.args.get('status')
    if status:
        q = q.filter(Visit.status == status)
    is_takeout = request.args.get('is_takeout')
    if is_takeout is not None:
        q = q.filter(Visit.is_takeout == (is_takeout.lower() in ('1', 'true')))
    visits = q.order_by(Visit.opened_at.desc()).all()
    return jsonify({'items': [v.to_dict() for v in visits]})


@visits_bp.get('/<int:visit_id>')
@roles_required('mesero', 'cajero', 'cocina', 'admin', 'superadmin')
def get_visit(visit_id):
    """Devuelve una visita con todas sus ordenes (una por comensal)."""
    visit = Visit.query.get_or_404(visit_id)
    return jsonify(visit.to_dict())


@visits_bp.post('')
@roles_required('mesero', 'cajero')
def create_visit():
    """Abre una mesa nueva (crea la Visit y una Order en borrador por cada
    comensal), O crea un pedido para llevar si is_takeout=true (una Visit sin
    mesa, con una sola Order, independiente de cualquier mesa fisica).

    Para mesas: falla si la mesa no existe o si ya tiene una visita activa
    (no se puede abrir la misma mesa dos veces al mismo tiempo). Para
    pedidos para llevar no aplica ninguna de las dos validaciones, ya que no
    hay mesa fisica que pueda estar "ocupada".
    """
    claims = get_jwt()
    data = request.get_json() or {}
    waiter_id = data.get('waiter_id') or claims.get('waiter_id')
    day_start, day_end = _local_day_utc_bounds(_tz_offset_minutes(data))

    if data.get('is_takeout'):
        customer_name = (data.get('customer_name') or '').strip() or None
        # Se toma el lock global de numeracion ANTES de leer cualquier
        # COUNT() (ver GLOBAL_LOCK_NAMESPACE arriba): sin esto, dos pedidos
        # para llevar simultaneos -o uno para llevar junto con la apertura
        # de una mesa- podian leer el mismo conteo antes de comitear y
        # terminar con el mismo folio del dia.
        _lock_daily_numbering()
        # Folio del dia solo para pedidos para llevar (1, 2, 3... por dia):
        # "Mesa {table_number}" ya identifica una visita de mesa sin
        # necesidad de folio aparte, asi que ahi se deja en None.
        takeout_daily_number = Visit.query.filter(
            Visit.is_takeout.is_(True), Visit.opened_at >= day_start, Visit.opened_at < day_end
        ).count() + 1
        visit = Visit(table_number=None, is_takeout=True, customer_name=customer_name, waiter_id=waiter_id, diners_count=1, daily_number=takeout_daily_number)
        db.session.add(visit)
        db.session.flush()
        db.session.add(Order(visit_id=visit.id, diner_index=1, waiter_id=waiter_id, status='borrador', daily_number=_next_order_daily_number(day_start, day_end)))
        db.session.commit()
        return jsonify(visit.to_dict()), 201

    table_number = data.get('table_number')
    diners = max(int(data.get('diners_count', 1)), 1)
    if not table_number:
        raise ApiError('table_number is required', 422, 'validation_error')
    table = Table.query.filter_by(number=int(table_number)).first()
    if not table:
        raise ApiError('Table not found', 404, 'table_not_found')
    if table.capacity and diners > table.capacity:
        raise ApiError(f'La mesa {table.number} tiene capacidad para {table.capacity} comensales', 422, 'over_capacity')
    db.session.execute(text('SELECT pg_advisory_xact_lock(:ns, :table_number)'), {'ns': TABLE_LOCK_NAMESPACE, 'table_number': table.number})
    existing = Visit.query.filter_by(table_number=table.number, status='active').first()
    if existing:
        raise ApiError('Table already has an active visit', 409, 'table_occupied')
    visit = Visit(table_number=table.number, waiter_id=waiter_id, diners_count=diners)
    db.session.add(visit)
    db.session.flush()
    _lock_daily_numbering()
    next_order_number = _next_order_daily_number(day_start, day_end)
    for offset, idx in enumerate(range(1, diners + 1)):
        db.session.add(Order(visit_id=visit.id, diner_index=idx, waiter_id=waiter_id, status='borrador', daily_number=next_order_number + offset))
    db.session.commit()
    return jsonify(visit.to_dict()), 201


@visits_bp.post('/<int:visit_id>/diners')
@roles_required('mesero', 'cajero')
def add_diner(visit_id):
    """Agrega un comensal mas a una mesa ya abierta (nueva Order en borrador con el siguiente diner_index)."""
    claims = get_jwt()
    data = request.get_json() or {}
    # Mismo lock por mesa que usa create_visit (TABLE_LOCK_NAMESPACE), pero
    # ahora keyeado por visit_id para que tambien sirva con pedidos "para
    # llevar" (sin table_number). Sin esto, dos altas de comensal casi
    # simultaneas en la MISMA visita leian el mismo "siguiente diner_index"
    # antes de comitear (creando dos Order con el mismo diner_index, sin
    # UniqueConstraint que lo impida) y pisaban el incremento de
    # diners_count del otro (lost update: quedaba +1 en vez de +2).
    db.session.execute(text('SELECT pg_advisory_xact_lock(:ns, :visit_id)'), {'ns': VISIT_LOCK_NAMESPACE, 'visit_id': visit_id})
    visit = Visit.query.get_or_404(visit_id)
    if visit.status != 'active':
        raise ApiError('Visit is not active', 409, 'visit_closed')
    if visit.table_number:
        table = Table.query.filter_by(number=visit.table_number).first()
        if table and table.capacity and (visit.diners_count or 0) + 1 > table.capacity:
            raise ApiError(f'La mesa {table.number} tiene capacidad para {table.capacity} comensales', 422, 'over_capacity')
    next_index = (max([o.diner_index for o in visit.orders]) + 1) if visit.orders else 1
    day_start, day_end = _local_day_utc_bounds(_tz_offset_minutes(data))
    _lock_daily_numbering()
    order = Order(visit_id=visit.id, diner_index=next_index, waiter_id=claims.get('waiter_id'), status='borrador', daily_number=_next_order_daily_number(day_start, day_end))
    db.session.add(order)
    visit.diners_count = (visit.diners_count or 0) + 1
    db.session.commit()
    return jsonify(visit.to_dict()), 201


@visits_bp.delete('/<int:visit_id>/diners/<int:diner_index>')
@roles_required('mesero', 'cajero')
def remove_diner(visit_id, diner_index):
    """Quita un comensal de la mesa. Solo se permite si su orden sigue en 'borrador' y no tiene platillos (para no perder un pedido ya en curso)."""
    visit = Visit.query.get_or_404(visit_id)
    order = Order.query.filter_by(visit_id=visit.id, diner_index=diner_index).first()
    if not order:
        raise ApiError('Diner not found', 404, 'diner_not_found')
    if order.status not in ('borrador',) or order.items:
        raise ApiError('Cannot remove a diner with items already ordered', 409, 'diner_not_removable')
    db.session.delete(order)
    visit.diners_count = max((visit.diners_count or 1) - 1, 0)
    db.session.commit()
    return jsonify(visit.to_dict())


@visits_bp.post('/<int:visit_id>/close')
@roles_required('mesero', 'cajero')
def close_visit(visit_id):
    """Cierra la mesa (la deja libre para el siguiente servicio). Falla si todavia hay ordenes con platillos sin pagar."""
    visit = Visit.query.get_or_404(visit_id)
    # Una orden con TODOS sus platillos cancelados no tiene nada pendiente
    # de cobrar (aunque o.items no este vacio: los platillos cancelados
    # siguen existiendo como registro, solo que no cuentan para esto).
    unpaid = [o for o in visit.orders if o.status not in ('pagado',) and any(it.status != 'cancelado' for it in o.items)]
    if unpaid:
        raise ApiError('There are unpaid orders for this table', 409, 'unpaid_orders')
    # Ordenes que se quedaron en borrador SIN ningun platillo (mesa abierta
    # por error, o un comensal de mas al que nunca se le pidio nada): no
    # dejan ningun rastro real que valga la pena conservar, asi que se
    # borran aqui mismo -- igual que remove_diner() ya hace con un comensal
    # individual mientras la mesa sigue activa. Sin esto, se quedaban en la
    # base de datos para siempre como "ordenes fantasma": nunca cambian de
    # estatus, pero seguian contando un folio del dia y apareciendo como
    # BORRADOR en "Ultimos pedidos" del dashboard mucho despues de que la
    # mesa ya estaba cerrada y libre.
    for order in list(visit.orders):
        if order.status == 'borrador' and not order.items:
            # visit.orders.remove(order), NO db.session.delete(order): la
            # relacion tiene cascade='all, delete-orphan' (ver Visit.orders
            # en models/entities.py), pero solo se activa -y solo se
            # refleja de inmediato en la coleccion en memoria de abajo- al
            # quitar el hijo de la coleccion del padre. Llamando
            # db.session.delete(order) directo, visit.orders seguia
            # trayendo estas ordenes ya borradas de la BD (coleccion en
            # memoria obsoleta), y diners_count se calculaba mal.
            visit.orders.remove(order)
    db.session.flush()
    # Sin esto, diners_count se quedaba con el conteo original (incluyendo
    # los comensales fantasma recien borrados arriba): el historico de la
    # mesa mostraba mas comensales de los que en realidad dejaron algun
    # registro. visit.orders ya refleja los borrados tras el flush().
    visit.diners_count = len(visit.orders)
    visit.status = 'closed'
    visit.closed_at = datetime.utcnow()
    db.session.commit()
    return jsonify(visit.to_dict())


IVA_RATE = 0.16
VALID_PAYMENT_METHODS = ['efectivo', 'tarjeta', 'transferencia', 'mixto']


def _distribute(total_amount, orders, order_subtotals, combined_subtotal):
    """Reparte total_amount entre orders proporcional a su subtotal, sin perder centavos por redondeo."""
    result = {}
    assigned_so_far = 0.0
    for idx, order in enumerate(orders):
        share = order_subtotals[order.id] / combined_subtotal if combined_subtotal else 1 / len(orders)
        if idx == len(orders) - 1:
            amount = round(total_amount - assigned_so_far, 2)
        else:
            amount = round(total_amount * share, 2)
            assigned_so_far += amount
        result[order.id] = amount
    return result


@visits_bp.post('/<int:visit_id>/pay')
@roles_required('cajero', 'admin', 'superadmin')
def pay_visit(visit_id):
    """Cobra en una sola cuenta todas las ordenes entregadas y pendientes de pago de la mesa.

    Requiere que haya una caja (CashSession) abierta: si la caja esta
    cerrada, no se permite ningun cobro (ver app/utils/cash.py).
    """
    session = require_open_register()
    # Serializa cobros concurrentes de la MISMA mesa (doble clic, o dos
    # cajeros cobrando la misma cuenta combinada a la vez): sin este lock,
    # dos requests casi simultaneos podian leer ambos "payable" con las
    # mismas ordenes en 'entregado' antes de que el primero comiteara
    # status='pagado', y ambos terminaban cobrando (y marcando pagado) la
    # misma cuenta dos veces.
    db.session.execute(text('SELECT pg_advisory_xact_lock(:ns, :visit_id)'), {'ns': VISIT_LOCK_NAMESPACE, 'visit_id': visit_id})
    visit = Visit.query.get_or_404(visit_id)
    payable = [o for o in visit.orders if o.status == 'entregado' and o.items]
    if not payable:
        raise ApiError('No hay cuentas por cobrar en esta mesa', 409, 'nothing_to_pay')

    data = request.get_json() or {}

    order_subtotals = {o.id: round(float(sum((it.quantity or 0) * float(it.unit_price or 0) for it in o.items if it.status != 'cancelado')), 2) for o in payable}
    combined_subtotal = round(sum(order_subtotals.values()), 2)

    discount_amount = round(float(data.get('discount_amount', 0) or 0), 2)
    if discount_amount < 0:
        raise ApiError('El descuento no puede ser negativo', 422, 'validation_error')
    if discount_amount > combined_subtotal:
        raise ApiError('El descuento no puede ser mayor al subtotal', 422, 'validation_error')

    apply_tax = bool(data.get('apply_tax', False))
    # Misma correccion que orders.py/pay(): el IVA se calcula sobre el
    # subtotal combinado YA NETO de descuento (no el bruto), para que la
    # tasa efectiva que build_draft_from_sale() reconstruye al facturar siga
    # siendo exactamente IVA_RATE (16%) y no una tasa no estandar cuando hay
    # descuento.
    combined_tax = round((combined_subtotal - discount_amount) * IVA_RATE, 2) if apply_tax else 0.0

    tip_type = data.get('tip_type', 'manual')
    if tip_type == 'porcentaje':
        percent = float(data.get('tip_percent', 0) or 0)
        if percent < 0:
            raise ApiError('La propina no puede ser negativa', 422, 'validation_error')
        if percent > 100:
            raise ApiError('La propina no puede ser mayor al 100%', 422, 'validation_error')
        combined_tip = round(combined_subtotal * percent / 100, 2)
    else:
        percent = None
        combined_tip = round(float(data.get('tip_amount', 0) or 0), 2)
        if combined_tip < 0:
            raise ApiError('La propina no puede ser negativa', 422, 'validation_error')

    payment_method = data.get('payment_method')
    if payment_method and payment_method not in VALID_PAYMENT_METHODS:
        raise ApiError('Metodo de pago invalido', 422, 'validation_error')

    received_amount = data.get('received_amount')
    combined_total = round(combined_subtotal + combined_tax - discount_amount + combined_tip, 2)
    if received_amount is not None and payment_method in ('efectivo', 'mixto') and round(float(received_amount), 2) < combined_total:
        raise ApiError('El monto recibido no puede ser menor al total a cobrar', 422, 'validation_error')

    # Pago mixto: cash_amount es la parte del total combinado que se cobro
    # en efectivo (el resto se asume tarjeta/transferencia), repartida entre
    # las ordenes igual que la propina/descuento/IVA (proporcional al
    # subtotal de cada una).
    cash_by_order = {}
    if payment_method == 'mixto':
        cash_amount = data.get('cash_amount')
        if cash_amount is None:
            raise ApiError('Falta indicar el monto en efectivo del pago mixto', 422, 'validation_error')
        cash_amount = round(float(cash_amount), 2)
        if cash_amount < 0 or cash_amount > combined_total:
            raise ApiError('El monto en efectivo no puede ser negativo ni mayor al total', 422, 'validation_error')
        cash_by_order = _distribute(cash_amount, payable, order_subtotals, combined_subtotal)

    tip_by_order = _distribute(combined_tip, payable, order_subtotals, combined_subtotal)
    discount_by_order = _distribute(discount_amount, payable, order_subtotals, combined_subtotal)
    tax_by_order = _distribute(combined_tax, payable, order_subtotals, combined_subtotal)
    received_by_order = _distribute(float(received_amount), payable, order_subtotals, combined_subtotal) if received_amount is not None else {}

    now = datetime.utcnow()
    for order in payable:
        order.tip_type = tip_type
        order.tip_percent = percent
        order.tip_amount = tip_by_order[order.id]
        order.discount_amount = discount_by_order[order.id]
        order.tax_amount = tax_by_order[order.id]
        order.payment_method = payment_method
        order.received_amount = received_by_order.get(order.id)
        order.cash_amount = cash_by_order.get(order.id)
        order.status = 'pagado'
        order.paid_at = now
        order.register_session_id = session.id

    log_action('visit.pay', 'visit', visit.id, f'Cobro combinado de la mesa (visita #{visit.id}) por ${combined_total:.2f}, {len(payable)} orden(es) ({payment_method or "sin metodo"}).')
    db.session.commit()
    return jsonify({
        'visit': visit.to_dict(),
        'subtotal': round(combined_subtotal, 2),
        'tax_amount': combined_tax,
        'discount_amount': discount_amount,
        'tip_amount': combined_tip,
        'total': combined_total,
        'change_amount': round(float(received_amount) - combined_total, 2) if received_amount is not None else None,
        'orders_paid': [o.id for o in payable],
        # Folios del dia de cada orden pagada, para el "Ticket #" del recibo
        # (ver SaleReceipt en el frontend) -- separado de orders_paid porque
        # ese sigue siendo el id real, usado para poder corregir el cobro.
        'orders_daily_numbers': [o.daily_number for o in payable],
        # Desglose por comensal del cobro combinado: antes se calculaba aqui
        # mismo (tip_by_order/discount_by_order/tax_by_order) para repartirlo
        # en cada Order, pero nunca se regresaba -- el recibo y la pantalla
        # de cobro solo podian mostrar el total conjunto, sin poder decir
        # cuanto le tocaba a cada comensal. Se regresa el mismo reparto
        # proporcional que ya se aplico de verdad a cada orden.
        'orders_breakdown': [
            {
                'order_id': o.id,
                'diner_index': o.diner_index,
                'daily_number': o.daily_number,
                'subtotal': round(order_subtotals[o.id], 2),
                'tax_amount': tax_by_order[o.id],
                'discount_amount': discount_by_order[o.id],
                'tip_amount': tip_by_order[o.id],
                'total': round(order_subtotals[o.id] + tax_by_order[o.id] - discount_by_order[o.id] + tip_by_order[o.id], 2),
            }
            for o in payable
        ],
    })


@visits_bp.post('/<int:visit_id>/unpay')
@roles_required('cajero', 'admin', 'superadmin')
def unpay_visit(visit_id):
    """Corrige el cobro conjunto de una mesa: regresa a 'entregado' las ordenes
    pagadas cuyos ids vengan en order_ids (normalmente todas las que se
    cobraron juntas), limpiando sus campos de pago, sin borrar platillos ni
    su historial. Requiere un motivo no vacio (mismo criterio que cancelar
    un platillo o corregir un cobro individual), que queda en la bitacora."""
    require_open_register()
    visit = Visit.query.get_or_404(visit_id)
    data = request.get_json() or {}
    reason = (data.get('reason') or '').strip()
    if not reason:
        raise ApiError('Indica el motivo de la correccion', 400, 'reason_required')
    order_ids = set(data.get('order_ids') or [])
    targets = [o for o in visit.orders if o.id in order_ids and o.status == 'pagado']
    if not targets:
        raise ApiError('No hay ordenes pagadas que corregir en esta mesa', 409, 'order_not_paid')
    for order in targets:
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
    log_action('visit.unpay', 'visit', visit.id, f'Corrigio el cobro conjunto de la mesa (visita #{visit.id}), {len(targets)} orden(es). Motivo: {reason[:255]}')
    db.session.commit()
    return jsonify({'visit': visit.to_dict(), 'orders_reverted': [o.id for o in targets]})
