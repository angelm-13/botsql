"""
Modelos de datos (SQLAlchemy).

Jerarquia principal: Table (mesa fisica) -> Visit (una mesa abierta, con N
comensales) -> Order (un comensal dentro de esa visita) -> OrderItem (un
platillo dentro de esa orden). Waiter/User son personas: User es la
cuenta con la que se inicia sesion (usuario/contrasena/rol), Waiter es el
mesero como tal (nombre, apodo, cuantas mesas puede atender); un User con
rol 'mesero' esta ligado a un Waiter via waiter_id.

CashSession es el corte de caja (turno): mientras no haya una sesion con
status='open', no se puede cobrar (ver app/utils/cash.py).

Todas las columnas de fecha/hora se guardan en UTC (datetime.utcnow());
SerializerMixin.to_dict() les agrega el sufijo 'Z' al serializarlas para
que el navegador las interprete como UTC y las muestre en la hora real
del dispositivo del usuario, en vez de tratarlas como si ya fueran hora
local (ver el comentario dentro de SerializerMixin.to_dict).
"""
from datetime import datetime, date
from decimal import Decimal
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db
from app.restaurante.utils.crypto import EncryptedString

class SerializerMixin:
    def to_dict(self):
        data = {}
        for c in self.__table__.columns:
            value = getattr(self, c.name)
            if hasattr(value, 'isoformat'):
                iso = value.isoformat()
                # Los datetimes se guardan en UTC (datetime.utcnow()). Si no se
                # marca la 'Z', el navegador los interpreta como si ya fueran
                # hora local del dispositivo (segun el estandar ECMA-262), lo
                # que corre el reloj y el contador de tiempos transcurridos
                # segun la zona horaria de quien lo ve. Con la 'Z', el
                # navegador convierte correctamente a la hora local real del
                # dispositivo del usuario.
                if isinstance(value, datetime) and value.tzinfo is None:
                    iso += 'Z'
                value = iso
            elif isinstance(value, Decimal):
                value = float(value)
            data[c.name] = value
        return data

class User(db.Model, SerializerMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), nullable=False)  # mesero, cocina, cajero, admin, superadmin (superadmin: soporte/auditoria del desarrollador, nunca asignable desde la app)
    is_active = db.Column(db.Boolean, default=True)
    waiter_id = db.Column(db.Integer, db.ForeignKey('waiters.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        data = super().to_dict()
        data.pop('password_hash', None)
        return data

class Waiter(db.Model, SerializerMixin):
    __tablename__ = 'waiters'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    nickname = db.Column(db.String(80), nullable=False)
    status = db.Column(db.String(30), default='active')
    max_tables = db.Column(db.Integer, nullable=False, default=15)

class Table(db.Model, SerializerMixin):
    __tablename__ = 'tables'
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer, unique=True, nullable=False)
    capacity = db.Column(db.Integer, nullable=False, default=4)
    location_description = db.Column(db.String(160), nullable=True)

class Guisado(db.Model, SerializerMixin):
    __tablename__ = 'guisados'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    is_active = db.Column(db.Boolean, default=True)

class Category(db.Model, SerializerMixin):
    """Categoria del menu (antes una lista fija en el codigo). `slug` es lo
    que se guarda en Dish.category -- se genera una sola vez al crear la
    categoria y ya no cambia, aunque el admin luego edite el nombre."""
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(40), unique=True, nullable=False)
    name = db.Column(db.String(60), nullable=False)
    icon = db.Column(db.String(20), nullable=False, default='utensils')
    color = db.Column(db.String(9), nullable=False, default='#71717a')
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, default=True)

class AuditLog(db.Model, SerializerMixin):
    """Bitacora de cambios administrativos (platillos/categorias/guisados,
    personal, apertura/cierre de caja, correcciones de cobro). No registra
    el flujo operativo normal (tomar pedidos, cobrar) -- solo lo que
    modifica la configuracion o los datos sensibles del sistema. Visible
    unicamente para el rol 'superadmin' (ver /api/admin/audit)."""
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    actor_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    actor_username = db.Column(db.String(80), nullable=False)
    actor_role = db.Column(db.String(30), nullable=False)
    action = db.Column(db.String(60), nullable=False)
    entity_type = db.Column(db.String(40), nullable=False)
    entity_id = db.Column(db.Integer, nullable=True)
    description = db.Column(db.Text, nullable=False)
    # index=True: list_audit_log() (solo superadmin) siempre ordena por
    # created_at desc; sin indice, esa consulta escanea la tabla completa
    # en cuanto la bitacora crece.
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

class Dish(db.Model, SerializerMixin):
    __tablename__ = 'dishes'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(140), nullable=False)
    description = db.Column(db.Text, nullable=True)
    # URL opcional a una foto del platillo (se muestra en la pantalla de
    # menu animado). Si esta vacio, la tarjeta del menu usa el icono de la
    # categoria en su lugar (ver CatIcon en el frontend).
    image_url = db.Column(db.String(500), nullable=True)
    # Medida/presentacion libre (ej. "355 ml", "600 ml", "1 L"): sobre todo
    # para bebidas embotelladas, donde el mismo platillo puede venderse en
    # mas de un tamano y el administrador necesita dejarlo claro en el menu.
    size_label = db.Column(db.String(40), nullable=True)
    icon = db.Column(db.String(10), nullable=False, default='plate')
    # index=True: GET /menu/dishes filtra por category en cada carga del
    # menu del mesero (varias veces por minuto, por cada mesero activo).
    category = db.Column(db.String(30), nullable=False, default='especialidad1', index=True)
    price = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    production_cost = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    requires_guisado = db.Column(db.Boolean, default=False)
    schedule = db.Column(db.String(10), nullable=False, default='all')
    # index=True: es el filtro default de casi cualquier consulta al
    # catalogo de platillos (ver menu.py: list_dishes filtra is_active=True
    # salvo que se pida include_inactive).
    is_active = db.Column(db.Boolean, default=True, index=True)
    __table_args__ = (
        db.CheckConstraint('price >= 0', name='ck_dishes_price_non_negative'),
        db.CheckConstraint('production_cost >= 0', name='ck_dishes_production_cost_non_negative'),
    )

    def is_available_today(self, today=None):
        today = today or date.today()
        weekday = today.weekday()
        if self.schedule == 'all':
            return True
        if self.schedule == 'weekday':
            return weekday <= 4
        if self.schedule == 'weekend':
            return weekday >= 5
        if self.schedule.isdigit():
            return int(self.schedule) == weekday
        return True

class Visit(db.Model, SerializerMixin):
    __tablename__ = 'visits'
    id = db.Column(db.Integer, primary_key=True)
    # Nullable a proposito: un pedido "para llevar" (is_takeout=True) no
    # ocupa ninguna mesa fisica, asi que no tiene table_number. Las visitas
    # de mesa normales SIEMPRE traen un table_number (se sigue validando en
    # visits.py al abrir mesa).
    table_number = db.Column(db.Integer, nullable=True)
    waiter_id = db.Column(db.Integer, db.ForeignKey('waiters.id'), nullable=True)
    diners_count = db.Column(db.Integer, nullable=False, default=1)
    # index=True: TablesView del mesero y varios reportes filtran
    # Visit.status=='active' constantemente (polling cada pocos segundos).
    status = db.Column(db.String(20), nullable=False, default='active', index=True)
    # Modulo de "para llevar": una Visit para llevar reusa exactamente el
    # mismo modelo Visit/Order que una mesa (una sola Order, diner_index=1),
    # solo que sin mesa asignada. customer_name es opcional (nombre o nota
    # para identificar el pedido al momento de la entrega, ya que no hay
    # numero de mesa que lo identifique).
    is_takeout = db.Column(db.Boolean, nullable=False, default=False)
    customer_name = db.Column(db.String(120), nullable=True)
    # Folio del dia para pedidos "para llevar" (1, 2, 3... y vuelve a
    # empezar en 1 al dia siguiente, hora LOCAL del dispositivo que abrio el
    # pedido -- ver create_visit() en routes/visits.py). Nulo en visitas de
    # mesa: ahi "Mesa {table_number}" ya identifica el lugar sin necesidad
    # de un folio aparte. Independiente de `id` (la llave primaria real),
    # que nunca deja de crecer y no debe mostrarse al personal/cliente.
    daily_number = db.Column(db.Integer, nullable=True)
    opened_at = db.Column(db.DateTime, default=datetime.utcnow)
    closed_at = db.Column(db.DateTime, nullable=True)
    orders = db.relationship('Order', backref='visit', cascade='all, delete-orphan', order_by='Order.diner_index')

    def to_dict(self):
        data = super().to_dict()
        orders_dicts = [o.to_dict() for o in self.orders]
        data['orders'] = orders_dicts
        data['total'] = round(float(sum(o['total'] for o in orders_dicts)), 2)
        return data

class Order(db.Model, SerializerMixin):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    # index=True: casi toda pantalla (tablero de cocina, cuentas por
    # cobrar, dashboard, reportes) filtra ordenes por visit_id o por status;
    # ambas se consultan en cada ciclo de polling (cada 3-8s por pantalla
    # abierta), asi que un table scan aqui escala mal con el volumen de
    # ordenes historicas.
    visit_id = db.Column(db.Integer, db.ForeignKey('visits.id'), nullable=False, index=True)
    diner_index = db.Column(db.Integer, nullable=False, default=1)
    waiter_id = db.Column(db.Integer, db.ForeignKey('waiters.id'), nullable=True)
    status = db.Column(db.String(40), default='borrador', index=True)
    tip_type = db.Column(db.String(20), nullable=True)
    tip_percent = db.Column(db.Numeric(5, 2), nullable=True)
    tip_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    payment_method = db.Column(db.String(20), nullable=True)  # efectivo, tarjeta, transferencia, mixto
    discount_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    tax_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    received_amount = db.Column(db.Numeric(10, 2), nullable=True)
    # Solo tiene valor cuando payment_method == 'mixto': la parte del total
    # que se cobro en efectivo (el resto se asume tarjeta/transferencia).
    # Sin esto, un pago mixto no aportaba nada al efectivo esperado del
    # corte de caja (ver _order_cash_amount en cashier.py).
    cash_amount = db.Column(db.Numeric(10, 2), nullable=True)
    # Que CashSession estaba abierta cuando se cobro esta orden (null si
    # nunca se ha pagado, o si se pago antes de que existiera esta columna).
    # Sin esto, cashier.py atribuia cada orden pagada a "la sesion cuyo
    # opened_at sea <= paid_at", solo por rango de fechas: si una orden se
    # corrige (unpay) y se vuelve a cobrar DESPUES de que la sesion original
    # ya cerro (con esa venta ya incluida en su fotografia final), la
    # reasignaba tambien a la sesion nueva que este abierta en ese momento,
    # contando el mismo efectivo dos veces entre dos cortes de caja
    # distintos. Guardar el id explicito hace que la atribucion sea la
    # sesion real en la que se cobro, sin importar cuando se corrija despues.
    register_session_id = db.Column(db.Integer, db.ForeignKey('cash_sessions.id'), nullable=True)
    # Folio del dia de ESTA orden (1, 2, 3... reinicia cada dia LOCAL,
    # asignado en create_visit()/add_diner() en routes/visits.py), para
    # mostrar "Pedido #"/"Ticket #" en tableros, dashboard y recibos sin
    # exponer el id real de la fila (que nunca reinicia y crece para
    # siempre). Se comparte una sola secuencia entre mesas y para llevar.
    daily_number = db.Column(db.Integer, nullable=True)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    sent_at = db.Column(db.DateTime, nullable=True)
    cooked_at = db.Column(db.DateTime, nullable=True)
    ready_at = db.Column(db.DateTime, nullable=True)
    delivered_at = db.Column(db.DateTime, nullable=True)
    paid_at = db.Column(db.DateTime, nullable=True)
    items = db.relationship('OrderItem', backref='order', cascade='all, delete-orphan')
    __table_args__ = (
        # Defensa en profundidad: la app ya valida estos montos en
        # orders.py/visits.py antes de cobrar, pero un CHECK a nivel de BD
        # cierra la puerta a que un bug futuro (o un acceso directo a la
        # BD) deje un monto negativo sin que la aplicacion lo note.
        db.CheckConstraint('tip_amount >= 0', name='ck_orders_tip_amount_non_negative'),
        db.CheckConstraint('discount_amount >= 0', name='ck_orders_discount_amount_non_negative'),
        db.CheckConstraint('tax_amount >= 0', name='ck_orders_tax_amount_non_negative'),
        db.CheckConstraint('received_amount IS NULL OR received_amount >= 0', name='ck_orders_received_amount_non_negative'),
        db.CheckConstraint('cash_amount IS NULL OR cash_amount >= 0', name='ck_orders_cash_amount_non_negative'),
    )

    def to_dict(self):
        data = super().to_dict()
        data['items'] = [item.to_dict() for item in self.items]
        # Los platillos cancelados nunca se cobran: se excluyen del subtotal,
        # aunque se siguen listando en items[] para que quede visible que existieron.
        # round() en ambos: sin el de subtotal, sumar varios unit_price tipo
        # 10.10 en float puede dar 30.299999999999997 en vez de 30.30. Sin el
        # de total, un descuento que cancela el subtotal EXACTO (ej. cortesia
        # del 100%) resta ese residuo binario y deja un total como
        # -3.552713678800501e-15 -- "$0.00" real, pero que el cajero veria
        # como "-$0.00" en pantalla en vez de "$0.00".
        data['subtotal'] = round(float(sum([(item.quantity or 0) * float(item.unit_price or 0) for item in self.items if item.status != 'cancelado'])), 2)
        data['total'] = round(data['subtotal'] + float(self.tax_amount or 0) - float(self.discount_amount or 0) + float(self.tip_amount or 0), 2)
        change = None
        if self.received_amount is not None:
            change = round(float(self.received_amount) - data['total'], 2)
        data['change_amount'] = change
        table_number = None
        is_takeout = False
        customer_name = None
        visit_daily_number = None
        # self.visit ya viene cargado via el backref definido en
        # Visit.orders -- reconsultarlo con Visit.query.get(self.visit_id)
        # (como antes) disparaba una consulta nueva por cada Order.to_dict(),
        # incluso cuando Visit.to_dict() ya habia cargado exactamente esa
        # misma fila un momento antes.
        v = self.visit
        if v:
            table_number = v.table_number
            is_takeout = v.is_takeout
            customer_name = v.customer_name
            visit_daily_number = v.daily_number
        data['table_number'] = table_number
        # Para que el frontend pueda distinguir un pedido "para llevar" (sin
        # mesa) de una mesa normal en cualquier lista/ticket que use esta
        # misma Order (cuentas por cobrar, recibo impreso, etc.).
        data['is_takeout'] = is_takeout
        data['customer_name'] = customer_name
        # Folio del pedido "para llevar" al que pertenece esta orden (ver
        # Visit.daily_number arriba); placeLabel() en el frontend lo usa en
        # vez de visit_id para mostrar "Para llevar #N".
        data['visit_daily_number'] = visit_daily_number
        return data

class OrderItem(db.Model, SerializerMixin):
    __tablename__ = 'order_items'
    id = db.Column(db.Integer, primary_key=True)
    # index=True en ambas: el tablero de cocina/entregas y el ticket del
    # mesero consultan items por order_id constantemente, y los reportes de
    # "top platillos"/mermas de inventario agrupan por dish_id sobre el
    # historico completo de ordenes.
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False, index=True)
    dish_id = db.Column(db.Integer, db.ForeignKey('dishes.id'), nullable=False, index=True)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    note = db.Column(db.String(255), nullable=True)
    guisado_1_id = db.Column(db.Integer, db.ForeignKey('guisados.id'), nullable=True)
    guisado_2_id = db.Column(db.Integer, db.ForeignKey('guisados.id'), nullable=True)
    combinado = db.Column(db.Boolean, default=False)
    # Cada platillo avanza por cocina/entregas de forma INDEPENDIENTE del resto
    # de platillos de la misma orden (ver _recompute_order_status en
    # routes/orders.py): antes, agregar un platillo a una orden ya entregada
    # regresaba TODA la orden a "pedido", haciendo que platillos ya servidos
    # parecieran pendientes otra vez. Nullable a proposito: las filas viejas
    # (de antes de este cambio) se rellenan una sola vez en init_db.py a partir
    # del estatus que ya tenia su orden, en vez de forzar aqui un default que
    # resucitaria platillos antiguos ya entregados/pagados como "pendientes".
    status = db.Column(db.String(40), nullable=True)
    sent_at = db.Column(db.DateTime, nullable=True)
    cooked_at = db.Column(db.DateTime, nullable=True)
    ready_at = db.Column(db.DateTime, nullable=True)
    delivered_at = db.Column(db.DateTime, nullable=True)
    # Cancelacion de UN platillo (no se borra, se marca -- igual filosofia
    # que la baja logica de Dish/Guisado/User): status pasa a 'cancelado' y
    # estos tres campos quedan como el rastro auditable de quien, cuando y
    # por que. Solo se puede llegar a 'cancelado' mientras el platillo no
    # haya alcanzado 'listo_para_entrega' (ver CANCELLABLE_ITEM_STATUSES en
    # routes/orders.py).
    cancelled_at = db.Column(db.DateTime, nullable=True)
    cancelled_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    cancel_reason = db.Column(db.String(255), nullable=True)
    dish = db.relationship('Dish')
    guisado_1 = db.relationship('Guisado', foreign_keys=[guisado_1_id])
    guisado_2 = db.relationship('Guisado', foreign_keys=[guisado_2_id])
    __table_args__ = (
        db.CheckConstraint('quantity > 0', name='ck_order_items_quantity_positive'),
        db.CheckConstraint('unit_price >= 0', name='ck_order_items_unit_price_non_negative'),
    )

    def to_dict(self):
        data = super().to_dict()
        data['dish'] = self.dish.to_dict() if self.dish else None
        data['guisado_1'] = self.guisado_1.to_dict() if self.guisado_1 else None
        data['guisado_2'] = self.guisado_2.to_dict() if self.guisado_2 else None
        return data

class Reservation(db.Model, SerializerMixin):
    __tablename__ = 'reservations'
    id = db.Column(db.Integer, primary_key=True)
    table_number = db.Column(db.Integer, nullable=True)
    name = db.Column(db.String(140), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    guests = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(40), default='pending')
    event_type = db.Column(db.String(80), nullable=True)

class InventoryItem(db.Model, SerializerMixin):
    __tablename__ = 'inventory_items'
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(160), nullable=False)
    quantity = db.Column(db.Numeric(12, 3), nullable=False, default=0)
    unit = db.Column(db.String(40), nullable=False)
    cost_per_unit = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    # Umbral para la alerta de "stock bajo" (ver GET /inventory/items,
    # campo calculado is_low_stock). 0 = sin alerta configurada para este
    # insumo.
    min_stock = db.Column(db.Numeric(12, 3), nullable=False, default=0)
    # Baja logica (mismo criterio que Dish/Guisado/Category): un insumo
    # dado de baja no se borra, solo deja de aparecer en el catalogo activo,
    # para no perder el historial de movimientos que ya lo referencian.
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    __table_args__ = (
        # La aplicacion ya impide que un movimiento deje quantity en
        # negativo (ver create_movement en routes/inventory.py); este CHECK
        # es la misma defensa en profundidad que el resto del esquema.
        db.CheckConstraint('quantity >= 0', name='ck_inventory_items_quantity_non_negative'),
        db.CheckConstraint('cost_per_unit >= 0', name='ck_inventory_items_cost_non_negative'),
        db.CheckConstraint('min_stock >= 0', name='ck_inventory_items_min_stock_non_negative'),
    )

    def to_dict(self):
        data = super().to_dict()
        data['is_low_stock'] = bool(self.min_stock and float(self.quantity) < float(self.min_stock))
        data['total_value'] = round(float(self.quantity) * float(self.cost_per_unit), 2)
        return data

class RecipeItem(db.Model, SerializerMixin):
    __tablename__ = 'recipe_items'
    id = db.Column(db.Integer, primary_key=True)
    dish_id = db.Column(db.Integer, db.ForeignKey('dishes.id'), nullable=False)
    inventory_item_id = db.Column(db.Integer, db.ForeignKey('inventory_items.id'), nullable=False)
    quantity = db.Column(db.Numeric(12, 3), nullable=False)
    unit = db.Column(db.String(40), nullable=False)

# Tipos de movimiento de inventario:
#   entrada -> compra/recepcion de mercancia (SIEMPRE suma al stock)
#   salida  -> consumo/uso manual fuera del flujo de ordenes (SIEMPRE resta)
#   merma   -> perdida (caducidad, rotura, derrame...) (SIEMPRE resta);
#              se separa de "salida" a proposito porque un restaurante
#              necesita reportar el costo de mermas por separado del
#              consumo normal, para control de costos.
#   ajuste  -> correccion manual tras un conteo fisico (puede sumar o
#              restar); el signo lo decide la diferencia entre lo que
#              habia en sistema y lo que se conto de verdad.
INVENTORY_MOVEMENT_TYPES = ('entrada', 'salida', 'merma', 'ajuste')

class InventoryMovement(db.Model, SerializerMixin):
    """Renglon de la bitacora de movimientos de un insumo: registra CADA
    entrada/salida/merma/ajuste, quien lo hizo y cuando, y deja una foto de
    la cantidad resultante despues de aplicarlo -- asi el historial se
    puede leer de corrido sin tener que recalcular nada."""
    __tablename__ = 'inventory_movements'
    id = db.Column(db.Integer, primary_key=True)
    # index=True en ambas: GET /inventory/movements filtra por insumo y
    # ordena/filtra por fecha en cada consulta de historial o de KPIs
    # (mermas/entradas/salidas "de este mes").
    inventory_item_id = db.Column(db.Integer, db.ForeignKey('inventory_items.id'), nullable=False, index=True)
    type = db.Column(db.String(20), nullable=False)
    # Delta YA CON SIGNO aplicado al stock (positivo en entrada/ajuste que
    # suma, negativo en salida/merma/ajuste que resta) -- no la cantidad
    # "cruda" que capturo el usuario, para que sumar esta columna sobre un
    # rango de fechas de directamente el balance neto sin tener que fijarse
    # en el tipo de cada renglon.
    quantity_delta = db.Column(db.Numeric(12, 3), nullable=False)
    # Costo unitario vigente AL MOMENTO del movimiento (para entradas, el
    # precio de compra de esa remesa; para salida/merma, el costo del
    # insumo en ese momento) -- se guarda aparte de InventoryItem.cost_per_unit
    # porque ese campo puede cambiar despues y no debe alterar el valor
    # historico de un movimiento ya registrado.
    unit_cost = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    reason = db.Column(db.String(255), nullable=True)
    resulting_quantity = db.Column(db.Numeric(12, 3), nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    inventory_item = db.relationship('InventoryItem')
    __table_args__ = (
        db.CheckConstraint('resulting_quantity >= 0', name='ck_inventory_movements_resulting_quantity_non_negative'),
    )

    def to_dict(self):
        data = super().to_dict()
        data['total_cost'] = round(abs(float(self.quantity_delta)) * float(self.unit_cost), 2)
        data['inventory_item_description'] = self.inventory_item.description if self.inventory_item else None
        data['inventory_item_unit'] = self.inventory_item.unit if self.inventory_item else None
        return data

class CashSession(db.Model, SerializerMixin):
    __tablename__ = 'cash_sessions'
    id = db.Column(db.Integer, primary_key=True)
    opened_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    opened_at = db.Column(db.DateTime, default=datetime.utcnow)
    opening_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    closed_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    closed_at = db.Column(db.DateTime, nullable=True)
    closing_amount = db.Column(db.Numeric(10, 2), nullable=True)
    expected_amount = db.Column(db.Numeric(10, 2), nullable=True)
    difference = db.Column(db.Numeric(10, 2), nullable=True)
    notes = db.Column(db.String(255), nullable=True)
    # index=True: require_open_register()/register_current() buscan la
    # sesion con status=='open' en cada cobro y en el polling del panel de
    # caja (cada 15s).
    status = db.Column(db.String(20), nullable=False, default='open', index=True)
    # Fotografia (JSON como texto) de las ventas de este turno al momento de
    # cerrar la caja: total por metodo de pago, propinas y numero de ordenes.
    # Se guarda aqui (en vez de solo calcularse al vuelo) para que el ticket
    # de "corte de caja" se pueda reimprimir despues tal cual quedo ese
    # turno, sin que una caja nueva mezcle o cambie esos numeros.
    sales_breakdown_json = db.Column(db.Text, nullable=True)


# =====================================================================
# Facturacion CFDI: un restaurante = un solo emisor, asi que Company y
# PacConfig son configuracion de una sola fila (patron "singleton" via
# get_singleton(), igual que en el proyecto hermano cotizador_demo). No
# hay concepto de "cliente" persistente aqui (a diferencia de cotizador_demo):
# el receptor de cada factura se captura al momento de facturar, porque un
# comensal de restaurante casi nunca es un cliente recurrente con perfil.
# =====================================================================

class Company(db.Model, SerializerMixin):
    """Datos fiscales del restaurante como EMISOR de CFDI."""
    __tablename__ = 'companies'
    id = db.Column(db.Integer, primary_key=True)
    razon_social = db.Column(db.String(255), nullable=True)
    rfc = db.Column(db.String(13), nullable=True)
    regimen_fiscal = db.Column(db.String(5), nullable=True)  # clave SAT, ej. '601'
    cp = db.Column(db.String(5), nullable=True)              # lugar de expedicion
    direccion = db.Column(db.String(255), nullable=True)
    # Serie de las facturas (folio consecutivo se calcula en la ruta al timbrar).
    serie = db.Column(db.String(10), nullable=False, default='F')

    @classmethod
    def get_singleton(cls):
        company = cls.query.first()
        if not company:
            company = cls(serie='F')
            db.session.add(company)
            db.session.commit()
        return company

    def is_complete(self):
        """True si ya hay lo minimo para poder timbrar (RFC, regimen, CP)."""
        return bool(self.rfc and self.regimen_fiscal and self.cp and self.razon_social)


class PacConfig(db.Model, SerializerMixin):
    """Proveedor de timbrado (PAC) configurado. 'mock' = timbrado simulado
    (sin validez fiscal, para probar sin credenciales); el resto son modos
    reales de Facturama."""
    __tablename__ = 'pac_config'
    id = db.Column(db.Integer, primary_key=True)
    provider = db.Column(db.String(40), nullable=False, default='mock')
    facturama_user = db.Column(db.String(255), nullable=True)
    facturama_password = db.Column(EncryptedString(512), nullable=True)

    @classmethod
    def get_singleton(cls):
        cfg = cls.query.first()
        if not cfg:
            cfg = cls(provider='mock')
            db.session.add(cfg)
            db.session.commit()
        return cfg

    def to_dict(self):
        return {
            'id': self.id,
            'provider': self.provider or 'mock',
            'facturama_user': self.facturama_user,
            # Nunca se manda la contrasena real al frontend, solo si ya hay una guardada.
            'has_password': bool(self.facturama_password),
        }


class Invoice(db.Model, SerializerMixin):
    """Factura (CFDI de Ingreso, o de Egreso si es nota de credito) emitida
    para una venta ya cobrada. `order_ids_json` guarda exactamente que
    ordenes cubre (una sola, o varias si fue un cobro combinado de mesa),
    igual que ya se rastrea en el recibo de venta del frontend."""
    __tablename__ = 'invoices'
    id = db.Column(db.Integer, primary_key=True)
    visit_id = db.Column(db.Integer, db.ForeignKey('visits.id'), nullable=True)
    order_ids_json = db.Column(db.Text, nullable=True)  # JSON: [order_id, ...]

    uuid = db.Column(db.String(36), unique=True, nullable=True)
    serie = db.Column(db.String(25), nullable=True)
    folio = db.Column(db.String(50), nullable=True)
    cfdi_type = db.Column(db.String(2), nullable=False, default='I')  # I=Ingreso, E=Egreso (nota de credito)
    status = db.Column(db.String(20), nullable=False, default='draft')  # draft, stamped, cancelled, error
    relacion_uuid = db.Column(db.String(36), nullable=True)  # nota de credito -> UUID de la factura original

    # Receptor (capturado al momento de facturar; no hay tabla de clientes).
    receptor_rfc = db.Column(db.String(13), nullable=True)
    receptor_nombre = db.Column(db.String(255), nullable=True)
    receptor_regimen_fiscal = db.Column(db.String(5), nullable=True)
    receptor_cp_fiscal = db.Column(db.String(5), nullable=True)
    receptor_email = db.Column(db.String(255), nullable=True)
    uso_cfdi = db.Column(db.String(5), nullable=False, default='G03')

    forma_pago = db.Column(db.String(4), nullable=True)
    metodo_pago = db.Column(db.String(4), nullable=False, default='PUE')
    moneda = db.Column(db.String(4), nullable=False, default='MXN')

    subtotal = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    iva_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    total = db.Column(db.Numeric(10, 2), nullable=False, default=0)

    # El XML timbrado se guarda como texto en la BD (no como archivo en
    # disco): el volumen de un restaurante es bajo, y asi ni el XML ni el
    # PDF (que se genera al vuelo a partir de este texto) dependen de que
    # el contenedor tenga un volumen persistente para /uploads.
    xml_content = db.Column(db.Text, nullable=True)

    pac_provider = db.Column(db.String(40), nullable=True)
    pac_response = db.Column(db.Text, nullable=True)
    error_message = db.Column(db.Text, nullable=True)

    cancel_status = db.Column(db.String(15), nullable=False, default='vigente')  # vigente, en_proceso, cancelado, rechazado
    cancelled_reason = db.Column(db.Text, nullable=True)
    cancelled_at = db.Column(db.DateTime, nullable=True)

    # Quien la emitio (username del JWT): para la bitacora de auditoria del
    # superadmin (log_action ya la registra tambien, esto es ademas un campo
    # directo en la factura para no tener que cruzar tablas para saber quien
    # la hizo).
    created_by = db.Column(db.String(80), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    stamped_at = db.Column(db.DateTime, nullable=True)

    items = db.relationship('InvoiceItem', backref='invoice', cascade='all, delete-orphan')

    def to_dict(self):
        data = super().to_dict()
        data['items'] = [it.to_dict() for it in self.items]
        visit = Visit.query.get(self.visit_id) if self.visit_id else None
        data['table_number'] = visit.table_number if visit else None
        data['is_takeout'] = visit.is_takeout if visit else False
        data['customer_name'] = visit.customer_name if visit else None
        data['visit_daily_number'] = visit.daily_number if visit else None
        return data


class InvoiceItem(db.Model, SerializerMixin):
    """Concepto (renglon) de la factura: una 'foto' inmutable de un platillo
    al momento de facturar, para que la factura no cambie si el platillo se
    edita/borra despues."""
    __tablename__ = 'invoice_items'
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    quantity = db.Column(db.Numeric(10, 2), nullable=False, default=1)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    subtotal = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    clave_prod_serv = db.Column(db.String(8), nullable=False, default='90101501')
    clave_unidad = db.Column(db.String(3), nullable=False, default='E48')
    iva_rate = db.Column(db.Numeric(5, 4), nullable=False, default=0)
    iva_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)


class DemoConfig(db.Model, SerializerMixin):
    """Reloj de la version freemium/de prueba (ver app/demo.py): una sola
    fila, con el momento en que arranco el periodo de prueba. Patron
    singleton identico a Company/PacConfig. started_at se fija UNA sola vez
    (la primera vez que algo pide get_singleton(), tipicamente seed.py en el
    primer arranque) y nunca se actualiza despues -- reiniciar el contenedor
    no reinicia el reloj, solo una base de datos nueva de verdad lo hace."""
    __tablename__ = 'demo_config'
    id = db.Column(db.Integer, primary_key=True)
    started_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    @classmethod
    def get_singleton(cls):
        cfg = cls.query.first()
        if not cfg:
            cfg = cls(started_at=datetime.utcnow())
            db.session.add(cfg)
            db.session.commit()
        return cfg


class LoginAttempt(db.Model):
    """Registro de un intento de login FALLIDO, usado por el freno anti
    fuerza-bruta de auth.py. Vive en la base de datos (no en un diccionario
    en memoria del proceso) a proposito: gunicorn en produccion corre con
    varios workers (procesos independientes, cada uno con su propia
    memoria), asi que un contador en memoria solo protegia contra ataques
    que le tocaran siempre al mismo worker -- con N workers, el limite real
    efectivo era N veces el limite configurado, y un reinicio del proceso
    (deploy, crash) lo reseteaba a cero. La tabla es compartida por todos
    los workers (y por cualquier replica futura del backend), asi que el
    limite es real sin importar cuantos procesos esten corriendo."""
    __tablename__ = 'login_attempts'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(160), nullable=False, index=True)
    attempted_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class RateLimitHit(db.Model):
    """Registro generico de "esta accion se llamo una vez" para el rate
    limiting de escritura sensible (ver utils/rate_limit.py) -- mismo
    patron que LoginAttempt (tabla en BD, no memoria del proceso, por la
    misma razon: varios workers de gunicorn no comparten memoria). A
    diferencia de LoginAttempt (solo falla de login), aqui se registra
    CADA llamada (exitosa o no) porque el limite es "cuantas veces se
    puede llamar", no "cuantas veces fallo"."""
    __tablename__ = 'rate_limit_hits'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(160), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
