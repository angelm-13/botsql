import json
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity
from sqlalchemy import func, desc, and_, or_, text
from app.extensions import db
from app.restaurante.models import Order, OrderItem, Dish, Waiter, Visit, CashSession
from app.restaurante.utils.security import roles_required
from app.restaurante.utils.errors import ApiError
from app.restaurante.utils.audit import log_action
from app.restaurante.utils.cash import register_open_hours, register_open_too_long
from app.restaurante.utils.rate_limit import rate_limited

"""
Rutas de cajero/admin: KPIs, dashboard operativo, reportes de venta, y
apertura/cierre de caja (CashSession).

Regla de negocio clave: no se puede cobrar (ver orders.py/visits.py) sin
una CashSession abierta -- eso mantiene el corte de caja (register/close)
consistente con las ventas reales de ese turno.
"""
cashier_bp = Blueprint('cashier', __name__)

# Namespace fijo para el advisory lock de register_open (misma tecnica que
# ya usa visits.py para abrir mesa): no hay ninguna UniqueConstraint a
# nivel de BD que impida dos filas CashSession con status='open' a la vez,
# asi que sin este lock, dos requests casi simultaneos (dos cajeros, o
# doble clic) podian pasar ambos el chequeo "no hay caja abierta" antes de
# que cualquiera comiteara, creando dos sesiones abiertas. Como el resto
# del modulo siempre toma "la mas reciente" (order_by(opened_at.desc())),
# la sesion vieja quedaba huerfana con un fondo inicial obsoleto y sin
# ventas atribuidas.
REGISTER_LOCK_NAMESPACE = 918276
REGISTER_LOCK_KEY = 1


def _get_tz_offset_minutes():
    """
    Lee tz_offset_minutes de la query string: son los minutos que hay que
    SUMAR a la hora local del dispositivo para obtener UTC (es exactamente
    lo que devuelve JS `Date.prototype.getTimezoneOffset()` en el
    navegador). El frontend lo manda en cada llamada a /kpis y /dashboard.

    Sin esto, "hoy" y las horas de los pedidos se calculaban con el reloj
    del servidor (normalmente UTC dentro del contenedor Docker), lo cual no
    coincide con la hora real del dispositivo del usuario, especialmente
    para restaurantes fuera de la zona UTC+0.
    """
    try:
        offset = int(request.args.get('tz_offset_minutes', 0))
    except (TypeError, ValueError):
        offset = 0
    # limite razonable: entre -14h y +12h de desfase
    return max(-840, min(720, offset))


def _to_local(dt, tz_offset_minutes):
    """Convierte un datetime UTC (naive) a la hora local real del dispositivo."""
    if dt is None:
        return None
    return dt - timedelta(minutes=tz_offset_minutes)


def _order_subtotal(order):
    # Los platillos cancelados nunca se cobraron: se excluyen de cualquier
    # calculo de ventas/ingresos derivado de aqui (kpis, dashboard, reportes).
    return float(sum((item.quantity or 0) * float(item.unit_price or 0) for item in order.items if item.status != 'cancelado'))


def _order_revenue(order):
    """Subtotal + IVA - descuento, SIN incluir la propina (que se reporta aparte)."""
    return _order_subtotal(order) + float(order.tax_amount or 0) - float(order.discount_amount or 0)


def _order_total_collected(order):
    """Lo que efectivamente se cobro por esta orden, incluyendo propina."""
    return _order_revenue(order) + float(order.tip_amount or 0)


def _order_cash_amount(order):
    """Cuanto de esta orden entro fisicamente como efectivo al cajon:
    todo si el metodo fue 'efectivo' (o no se especifico), la parte
    guardada en cash_amount si fue 'mixto', nada si fue tarjeta/transferencia."""
    method = order.payment_method or 'efectivo'
    if method == 'efectivo':
        return _order_total_collected(order)
    if method == 'mixto':
        return float(order.cash_amount or 0)
    return 0.0


def _session_summary(session):
    """Resumen de ventas de la sesion de caja ABIERTA `session`, calculado
    en vivo (sin cerrar nada) para que el cajero vea cuanto se espera antes
    de contar el cajon. register_close() usa el mismo calculo para dejar la
    fotografia final en sales_breakdown_json."""
    # register_session_id (asignado en pay()/pay_visit() al cobrar) es la
    # fuente de verdad de a que turno pertenece una orden pagada. Se hace
    # fallback al filtro anterior por fecha (paid_at >= session.opened_at)
    # SOLO para ordenes pagadas antes de que existiera esta columna
    # (register_session_id IS NULL) -- sin el fallback, ventas de antes de
    # este cambio desaparecerian de cualquier corte de caja.
    paid_orders = Order.query.filter(
        Order.status == 'pagado',
        or_(
            Order.register_session_id == session.id,
            and_(Order.register_session_id.is_(None), Order.paid_at >= session.opened_at),
        ),
    ).all()
    payment_breakdown = {}
    for o in paid_orders:
        method = o.payment_method or 'efectivo'
        payment_breakdown[method] = payment_breakdown.get(method, 0) + _order_total_collected(o)
    cash_expected = round(float(session.opening_amount) + sum(_order_cash_amount(o) for o in paid_orders), 2)
    return {
        'orders_count': len(paid_orders),
        'total_sales': round(sum(_order_revenue(o) for o in paid_orders), 2),
        'total_tips': round(sum(float(o.tip_amount or 0) for o in paid_orders), 2),
        'payment_breakdown': {k: round(v, 2) for k, v in payment_breakdown.items()},
        'cash_collected': round(sum(_order_cash_amount(o) for o in paid_orders), 2),
        'cash_expected': cash_expected,
    }


@cashier_bp.get('/kpis')
@roles_required('cajero', 'admin', 'superadmin')
def kpis():
    """Indicadores para el cajero/admin: ventas y propinas del turno actual (caja
    abierta), ticket promedio, desglose por metodo de pago, mesas activas,
    y rankings historicos (platillos/mesas/meseros mas frecuentes).

    total_sales/tips/avg_ticket/payment_breakdown estan escopados a la
    CashSession abierta actualmente (se reinician cada vez que se abre una
    caja nueva); top_dishes/top_tables/services_by_waiter son historicos
    (de siempre), pensados como un ranking, no como venta del turno.
    """
    current_session = CashSession.query.filter_by(status='open').order_by(CashSession.opened_at.desc()).first()
    if current_session:
        # Mismo criterio que _session_summary: register_session_id primero,
        # con fallback por fecha solo para ordenes pagadas antes de que
        # existiera esa columna.
        session_paid_orders = Order.query.filter(
            Order.status == 'pagado',
            or_(
                Order.register_session_id == current_session.id,
                and_(Order.register_session_id.is_(None), Order.paid_at >= current_session.opened_at),
            ),
        ).all()
    else:
        session_paid_orders = []

    total_sales = sum(_order_revenue(o) for o in session_paid_orders)
    tips = sum(float(o.tip_amount or 0) for o in session_paid_orders)
    paid_orders_count = len(session_paid_orders)
    avg_ticket = round((total_sales + tips) / paid_orders_count, 2) if paid_orders_count else 0

    payment_breakdown = {}
    for o in session_paid_orders:
        method = o.payment_method or 'sin_especificar'
        payment_breakdown[method] = payment_breakdown.get(method, 0) + _order_total_collected(o)
    payment_breakdown = {k: round(v, 2) for k, v in payment_breakdown.items()}

    # OrderItem.status != 'cancelado': sin este filtro, un platillo cancelado
    # 8 de 10 veces (por ejemplo por falta de insumo) aparecia en el ranking
    # como si se hubiera vendido las 10, aunque el ingreso real solo
    # reflejara las 2 que si se entregaron y cobraron -- inconsistente con
    # _order_subtotal, que si excluye cancelados en todos los demas totales.
    top_dishes = db.session.query(Dish.title, func.sum(OrderItem.quantity).label('qty')) \
        .join(OrderItem, Dish.id == OrderItem.dish_id) \
        .join(Order, Order.id == OrderItem.order_id) \
        .filter(Order.status == 'pagado', OrderItem.status != 'cancelado') \
        .group_by(Dish.title).order_by(desc('qty')).limit(5).all()

    # Se excluyen los pedidos "para llevar" (table_number None): agruparlos
    # aqui produciria un renglon "Mesa None" sin sentido en un ranking que es
    # especificamente de mesas fisicas.
    top_tables = (
        db.session.query(Visit.table_number, func.count(Order.id).label('services'))
        .join(Order, Visit.id == Order.visit_id)
        .filter(Order.status == 'pagado', Visit.is_takeout == False)  # noqa: E712 -- comparacion de columna SQLAlchemy, no un bool de Python
        .group_by(Visit.table_number).order_by(desc('services')).limit(5).all()
    )

    services_by_waiter = db.session.query(Waiter.nickname, func.count(Order.id).label('services')) \
        .outerjoin(Order, and_(Waiter.id == Order.waiter_id, Order.status == 'pagado')) \
        .group_by(Waiter.nickname).order_by(desc('services')).all()

    # Se calcula solo con las entregas de HOY (no historico completo), para que
    # este numero refleje el desempeno real del turno actual y no se diluya con
    # datos de dias anteriores. 'Hoy' se calcula en la hora local real del
    # dispositivo (tz_offset_minutes), igual que en /dashboard.
    tz_offset_minutes = _get_tz_offset_minutes()
    today_local = _to_local(datetime.utcnow(), tz_offset_minutes).date()
    utc_lower_bound = datetime.utcnow() - timedelta(hours=48)
    diffs = []
    for order in Order.query.filter(
        Order.ready_at.isnot(None), Order.delivered_at.isnot(None), Order.delivered_at >= utc_lower_bound
    ).all():
        if _to_local(order.delivered_at, tz_offset_minutes).date() == today_local:
            diffs.append((order.delivered_at - order.ready_at).total_seconds() / 60)
    avg_delivery_time = round(sum(diffs) / len(diffs), 2) if diffs else 0

    return jsonify({
        'total_sales': round(total_sales, 2),
        'tips': round(tips, 2),
        'top_dishes': [{'dish': t[0], 'quantity': int(t[1])} for t in top_dishes],
        'dish_frequency': [{'dish': t[0], 'frequency': int(t[1])} for t in top_dishes],
        'top_tables': [{'table': t[0], 'services': int(t[1])} for t in top_tables],
        'services_by_waiter': [{'waiter': t[0], 'services': int(t[1])} for t in services_by_waiter],
        'avg_minutes_from_ready_to_delivered': avg_delivery_time,
        'avg_ticket': avg_ticket,
        'active_tables': Visit.query.filter_by(status='active', is_takeout=False).count(),
        'active_takeout_orders': Visit.query.filter_by(status='active', is_takeout=True).count(),
        'register_open': current_session is not None,
        # 'Z' al final: opened_at se guarda en UTC (datetime.utcnow()) pero
        # isoformat() no lo marca por su cuenta -- sin la 'Z', el navegador
        # interpreta la hora como si ya fuera local (ver SerializerMixin.
        # to_dict en models/entities.py, que hace lo mismo para todo lo
        # demas) y "Caja abierta" salia con la hora UTC del servidor en vez
        # de la hora real del dispositivo del usuario.
        'register_opened_at': (current_session.opened_at.isoformat() + 'Z') if current_session else None,
        # Aviso (no bloqueante) de que la caja lleva abierta mas de lo
        # normal -- ver REGISTER_OPEN_ALERT_HOURS en utils/cash.py. Casi
        # siempre significa que alguien olvido cerrarla, no que el turno de
        # verdad sigue activo.
        'register_open_too_long': register_open_too_long(current_session),
        'payment_breakdown': payment_breakdown,
    })


def _orders_on_local_date(candidate_orders, target_date, tz_offset_minutes):
    # Se excluyen ordenes sin ningun platillo: son "ordenes fantasma" que
    # quedan cuando se abre una mesa por error (o por accidente) y se cierra
    # sin pedir nada -- close_visit() permite cerrar una mesa asi porque no
    # hay nada pendiente de cobrar, pero la Order en 'borrador' seguia
    # contando en pedidos de hoy, mesas atendidas y pedidos por hora aunque
    # nunca hubo un pedido real. Cualquier orden real (enviada a cocina)
    # siempre tiene al menos un platillo (ver send_to_kitchen), asi que este
    # filtro no afecta ninguna orden legitima.
    return [
        o for o in candidate_orders
        if o.items and o.started_at and _to_local(o.started_at, tz_offset_minutes).date() == target_date
    ]


def _day_metrics(day_orders):
    """Los mismos 5 indicadores de 'hoy' del dashboard, para cualquier dia ya
    filtrado -- se reusa tal cual para 'ayer', y asi mostrar una comparacion
    real (no inventada) en las tarjetas de KPI del dashboard."""
    prep_diffs = [(o.ready_at - o.sent_at).total_seconds() / 60 for o in day_orders if o.sent_at and o.ready_at]
    return {
        'orders': len(day_orders),
        'items_requested': sum(sum(it.quantity or 0 for it in o.items if it.status != 'cancelado') for o in day_orders),
        'tables_served': len({o.visit_id for o in day_orders if o.visit_id}),
        'items_ready': sum(sum(it.quantity or 0 for it in o.items if it.status != 'cancelado') for o in day_orders if o.ready_at is not None),
        'items_cancelled': sum(1 for o in day_orders for it in o.items if it.status == 'cancelado'),
        'avg_prep_minutes': round(sum(prep_diffs) / len(prep_diffs), 1) if prep_diffs else 0,
    }


@cashier_bp.get('/dashboard')
@roles_required('cajero', 'admin', 'superadmin')
def dashboard():
    """Resumen operativo del dia: pedidos, platillos, mesas, tiempos, distribucion de estatus,
    ultimos pedidos y resumen por categoria. Todo calculado con datos reales, no estatico.

    'Hoy' y la hora de cada pedido se calculan en la hora LOCAL real del
    dispositivo (ver _get_tz_offset_minutes), no en el reloj UTC del
    servidor, para que el histograma de pedidos por hora y el corte de
    'hoy' coincidan con lo que el usuario ve en su reloj.
    """
    tz_offset_minutes = _get_tz_offset_minutes()

    # Traemos un rango amplio en UTC (ultimas 72h, suficiente incluso en los
    # desfases de zona horaria mas extremos que aceptamos) y afinamos la
    # fecha local exacta en Python: esto cubre correctamente el caso de
    # medianoche, donde la fecha UTC del servidor y la fecha local del
    # dispositivo no coinciden. Se amplio de 48h a 72h para tambien poder
    # calcular los mismos indicadores de AYER (comparacion en el dashboard)
    # sin una segunda consulta a la base de datos.
    utc_lower_bound = datetime.utcnow() - timedelta(hours=72)
    candidate_orders = Order.query.filter(Order.started_at >= utc_lower_bound).all()
    today = _to_local(datetime.utcnow(), tz_offset_minutes).date()
    yesterday = today - timedelta(days=1)
    orders_today = _orders_on_local_date(candidate_orders, today, tz_offset_minutes)
    orders_yesterday = _orders_on_local_date(candidate_orders, yesterday, tz_offset_minutes)

    today_metrics = _day_metrics(orders_today)
    yesterday_metrics = _day_metrics(orders_yesterday)
    orders_today_count = today_metrics['orders']
    items_requested_today = today_metrics['items_requested']
    tables_served_today = today_metrics['tables_served']
    items_ready_today = today_metrics['items_ready']
    items_cancelled_today = today_metrics['items_cancelled']
    avg_prep_minutes = today_metrics['avg_prep_minutes']

    hour_counts = {h: 0 for h in range(24)}
    for o in orders_today:
        if o.started_at:
            hour_counts[_to_local(o.started_at, tz_offset_minutes).hour] += 1
    orders_by_hour = [{'hour': h, 'count': hour_counts[h]} for h in range(24)]

    status_counts = {}
    for o in orders_today:
        status_counts[o.status] = status_counts.get(o.status, 0) + 1

    # Mismo criterio que _orders_on_local_date (arriba): una orden sin
    # ningun platillo (mesa abierta por error y cerrada sin pedir nada, o un
    # comensal de mas al que nunca se le pidio nada) no es un pedido real
    # todavia. Antes esta lista no filtraba esto, asi que ese tipo de ordenes
    # aparecian en "Ultimos pedidos" como BORRADOR indefinidamente, aunque la
    # mesa ya estuviera cerrada y libre (close_visit ahora tambien las borra
    # al cerrar, pero esto cubre el caso en lo que la mesa sigue activa).
    recent = Order.query.filter(Order.items.any()).order_by(Order.started_at.desc()).limit(8).all()
    recent_orders = []
    for o in recent:
        data = o.to_dict()
        # Se marca (cancelado) junto al platillo que se cancelo dentro de la
        # orden -- sin esto, una orden con un platillo cancelado y otro
        # entregado se veia identica a una orden donde se entregaron los
        # dos, porque el resumen solo listaba nombres sin distinguir cual
        # en realidad no se sirvio.
        items_summary = ', '.join(
            f"{it.quantity}x {it.dish.title}{' (cancelado)' if it.status == 'cancelado' else ''}"
            for it in o.items if it.dish
        ) or '-'
        recent_orders.append({
            'id': o.id,
            # Folio del dia de esta orden (columna "PEDIDO" en el dashboard)
            # y de la visita para llevar a la que pertenece (para que
            # placeLabel() en el frontend muestre "Para llevar #N" con el
            # folio diario en vez del id real, que nunca reinicia).
            'daily_number': data.get('daily_number'),
            'visit_daily_number': data.get('visit_daily_number'),
            'table_number': data.get('table_number'),
            'is_takeout': data.get('is_takeout'),
            'customer_name': data.get('customer_name'),
            'diner_index': o.diner_index,
            # Se reusa data['started_at'] (ya trae la 'Z' que le agrega
            # SerializerMixin.to_dict) en vez de volver a llamar
            # started_at.isoformat() aqui, que la omitia y hacia que el
            # navegador mostrara la hora UTC del servidor como si fuera
            # local (mismo bug que register_opened_at, arriba en kpis()).
            'time': data.get('started_at'),
            'items_summary': items_summary,
            'status': o.status,
        })

    category_qty = {}
    for o in orders_today:
        for it in o.items:
            if it.status == 'cancelado':
                continue
            cat = it.dish.category if it.dish else 'otro'
            category_qty[cat] = category_qty.get(cat, 0) + (it.quantity or 0)
    total_items = sum(category_qty.values())
    category_breakdown = [
        {'category': cat, 'quantity': qty, 'percent': round(qty / total_items * 100, 1) if total_items else 0}
        for cat, qty in sorted(category_qty.items(), key=lambda x: -x[1])
    ]

    return jsonify({
        'date': today.isoformat(),
        'orders_today': orders_today_count,
        'items_requested_today': items_requested_today,
        'tables_served_today': tables_served_today,
        'items_ready_today': items_ready_today,
        'items_cancelled_today': items_cancelled_today,
        'avg_prep_minutes_today': avg_prep_minutes,
        'orders_by_hour': orders_by_hour,
        'status_distribution': status_counts,
        'recent_orders': recent_orders,
        'category_breakdown': category_breakdown,
        # Mismos 5 indicadores pero de AYER, para que el frontend pueda
        # mostrar una comparacion real ("+20% vs ayer") en vez de un numero
        # suelto sin contexto.
        'previous_day': {'date': yesterday.isoformat(), **yesterday_metrics},
    })


@cashier_bp.get('/reports')
@roles_required('cajero', 'admin', 'superadmin')
def sales_report():
    """Reporte de ventas por rango de fechas, agrupado por dia (usado para exportar el PDF de reportes).

    `start`/`end` llegan como fechas de calendario LOCALES (ej. "2026-08-11",
    ver fmtLocalDate en el frontend) -- igual que /kpis y /dashboard, hay que
    convertirlas a limites UTC usando tz_offset_minutes antes de comparar
    contra Order.paid_at (que se guarda en UTC). Sin esto, un restaurante
    fuera de UTC+0 recibia un reporte "de hoy" que en realidad incluia horas
    del dia anterior/siguiente y excluia parte del dia real seleccionado.
    """
    tz_offset_minutes = _get_tz_offset_minutes()
    start = request.args.get('start')
    end = request.args.get('end')
    q = Order.query.filter(Order.status == 'pagado')
    if start:
        start_local_midnight = datetime.fromisoformat(start)
        q = q.filter(Order.paid_at >= start_local_midnight + timedelta(minutes=tz_offset_minutes))
    if end:
        end_local_midnight_next_day = datetime.fromisoformat(end) + timedelta(days=1)
        q = q.filter(Order.paid_at < end_local_midnight_next_day + timedelta(minutes=tz_offset_minutes))
    orders = q.order_by(Order.paid_at.asc()).all()
    by_day = {}
    for o in orders:
        day = _to_local(o.paid_at, tz_offset_minutes).date().isoformat() if o.paid_at else 'sin_fecha'
        bucket = by_day.setdefault(day, {'date': day, 'orders': 0, 'sales': 0.0, 'tips': 0.0})
        bucket['orders'] += 1
        bucket['sales'] += _order_revenue(o)
        bucket['tips'] += float(o.tip_amount or 0)
    days = sorted(by_day.values(), key=lambda x: x['date'])
    for d in days:
        d['sales'] = round(d['sales'], 2)
        d['tips'] = round(d['tips'], 2)
    return jsonify({
        'days': days,
        'total_orders': len(orders),
        'total_sales': round(sum(d['sales'] for d in days), 2),
        'total_tips': round(sum(d['tips'] for d in days), 2),
    })


@cashier_bp.get('/register/current')
@roles_required('cajero', 'admin', 'superadmin')
def register_current():
    """Devuelve la caja abierta actualmente, o null si no hay ninguna abierta.

    Si hay una abierta, incluye `live_summary` (ver _session_summary): el
    desglose de ventas EN VIVO de este turno, para que el cajero vea cuanto
    se espera encontrar en el cajon antes de contarlo, sin tener que cerrar
    la caja para averiguarlo."""
    session = CashSession.query.filter_by(status='open').order_by(CashSession.opened_at.desc()).first()
    if not session:
        return jsonify(None)
    data = session.to_dict()
    data['live_summary'] = _session_summary(session)
    # Mismo aviso que kpis() -- ver REGISTER_OPEN_ALERT_HOURS en utils/cash.py.
    data['open_hours'] = round(register_open_hours(session), 1)
    data['open_too_long'] = register_open_too_long(session)
    return jsonify(data)


@cashier_bp.get('/register/history')
@roles_required('cajero', 'admin', 'superadmin')
def register_history():
    """Historial de los ultimos 30 cortes de caja (abiertos y cerrados)."""
    sessions = CashSession.query.order_by(CashSession.opened_at.desc()).limit(30).all()
    return jsonify({'items': [s.to_dict() for s in sessions]})


@cashier_bp.post('/register/open')
@roles_required('cajero', 'admin', 'superadmin')
@rate_limited('register_open', max_requests=10, window_seconds=60)
def register_open():
    """Abre una caja nueva con un monto inicial. Falla si ya hay una caja abierta (no se permite abrir dos a la vez)."""
    db.session.execute(text('SELECT pg_advisory_xact_lock(:ns, :key)'), {'ns': REGISTER_LOCK_NAMESPACE, 'key': REGISTER_LOCK_KEY})
    existing = CashSession.query.filter_by(status='open').first()
    if existing:
        raise ApiError('There is already an open cash register', 409, 'register_already_open')
    data = request.get_json() or {}
    opening_amount = float(data.get('opening_amount', 0) or 0)
    if opening_amount < 0:
        raise ApiError('El monto de apertura no puede ser negativo', 422, 'validation_error')
    session = CashSession(
        opened_by_id=int(get_jwt_identity()),
        opening_amount=opening_amount,
        status='open',
    )
    db.session.add(session)
    db.session.flush()
    log_action('register.open', 'cash_session', session.id, f'Abrio la caja con ${session.opening_amount} de fondo inicial.')
    db.session.commit()
    return jsonify(session.to_dict()), 201


@cashier_bp.post('/register/close')
@roles_required('cajero', 'admin', 'superadmin')
@rate_limited('register_close', max_requests=10, window_seconds=60)
def register_close():
    """Cierra la caja abierta actualmente: calcula el efectivo esperado
    (solo lo cobrado en efectivo, no tarjeta/transferencia) y la
    diferencia contra lo que el cajero cuenta fisicamente.
    """
    session = CashSession.query.filter_by(status='open').order_by(CashSession.opened_at.desc()).first()
    if not session:
        raise ApiError('There is no open cash register', 409, 'register_not_open')
    data = request.get_json() or {}
    closing_amount = round(float(data.get('closing_amount', 0) or 0), 2)
    if closing_amount < 0:
        raise ApiError('El monto de cierre no puede ser negativo', 422, 'validation_error')
    summary = _session_summary(session)
    session.expected_amount = summary['cash_expected']
    session.closing_amount = closing_amount
    session.difference = round(session.closing_amount - session.expected_amount, 2)
    session.notes = data.get('notes')
    session.closed_by_id = int(get_jwt_identity())
    session.closed_at = datetime.utcnow()
    session.status = 'closed'

    # Se guarda una fotografia de las ventas de este turno (desglose por
    # metodo de pago, propinas y numero de ordenes) para poder imprimir o
    # reimprimir el ticket de "corte de caja" con los numeros exactos de
    # ESTE turno, aunque despues se abran otras cajas.
    session.sales_breakdown_json = json.dumps({
        'orders_count': summary['orders_count'],
        'total_sales': summary['total_sales'],
        'total_tips': summary['total_tips'],
        'payment_breakdown': summary['payment_breakdown'],
        'cash_collected': summary['cash_collected'],
    })

    log_action('register.close', 'cash_session', session.id, f'Cerro la caja. Esperado: ${session.expected_amount}, contado: ${session.closing_amount}, diferencia: ${session.difference}.')
    db.session.commit()
    return jsonify(session.to_dict())
