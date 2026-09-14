from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


def _value(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)) or hasattr(value, "isoformat"):
        return value.isoformat()
    return value


class RestaurantRecord:
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("user.id_user"), nullable=False)
    creation_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
    deletion_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def serialize_columns(self) -> dict:
        return {column.name: _value(getattr(self, column.name)) for column in self.__table__.columns}


class RestaurantWaiter(RestaurantRecord, Base):
    __tablename__ = "restaurant_waiter"

    id_restaurant_waiter: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_proyect: Mapped[int] = mapped_column(Integer, ForeignKey("proyect.id_proyect"), nullable=False, index=True)
    id_user: Mapped[int | None] = mapped_column(Integer, ForeignKey("user.id_user"), nullable=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    nickname: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")
    max_tables: Mapped[int] = mapped_column(Integer, nullable=False, default=15)

    def serialize(self) -> dict:
        return self.serialize_columns()


class RestaurantTable(RestaurantRecord, Base):
    __tablename__ = "restaurant_table"
    __table_args__ = (UniqueConstraint("id_proyect", "number", name="uq_restaurant_table_project_number"),)

    id_restaurant_table: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_proyect: Mapped[int] = mapped_column(Integer, ForeignKey("proyect.id_proyect"), nullable=False, index=True)
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    location_description: Mapped[str | None] = mapped_column(String(160), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    def serialize(self) -> dict:
        return self.serialize_columns()


class RestaurantGuisado(RestaurantRecord, Base):
    __tablename__ = "restaurant_guisado"

    id_restaurant_guisado: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_proyect: Mapped[int] = mapped_column(Integer, ForeignKey("proyect.id_proyect"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    def serialize(self) -> dict:
        return self.serialize_columns()


class RestaurantDish(RestaurantRecord, Base):
    __tablename__ = "restaurant_dish"

    id_restaurant_dish: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_proyect: Mapped[int] = mapped_column(Integer, ForeignKey("proyect.id_proyect"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(140), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    icon: Mapped[str] = mapped_column(String(40), nullable=False, default="plate")
    category: Mapped[str] = mapped_column(String(30), nullable=False, default="taco")
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    production_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    requires_guisado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    schedule: Mapped[str] = mapped_column(String(10), nullable=False, default="all")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    def is_available_today(self, today: date | None = None) -> bool:
        weekday = (today or date.today()).weekday()
        if self.schedule == "weekday":
            return weekday <= 4
        if self.schedule == "weekend":
            return weekday >= 5
        if self.schedule.isdigit():
            return int(self.schedule) == weekday
        return True

    def serialize(self) -> dict:
        return self.serialize_columns()


class RestaurantCategory(RestaurantRecord, Base):
    """Categoria del menu, editable por proyecto.

    Antes las categorias eran un set fijo en el servicio (DISH_CATEGORIES),
    asi que un restaurante no podia agregar las suyas. La columna
    restaurant_dish.category sigue guardando el slug como texto: esta tabla
    es el catalogo que lo valida y le da nombre, icono y orden de
    presentacion, sin migrar los platillos existentes.
    """

    __tablename__ = "restaurant_category"
    __table_args__ = (
        UniqueConstraint("id_proyect", "slug", name="uq_restaurant_category_project_slug"),
    )

    id_restaurant_category: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_proyect: Mapped[int] = mapped_column(Integer, ForeignKey("proyect.id_proyect"), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(30), nullable=False)
    label: Mapped[str] = mapped_column(String(80), nullable=False)
    icon: Mapped[str] = mapped_column(String(40), nullable=False, default="plate")
    color: Mapped[str | None] = mapped_column(String(20), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    def serialize(self) -> dict:
        return self.serialize_columns()


class RestaurantVisit(RestaurantRecord, Base):
    __tablename__ = "restaurant_visit"

    id_restaurant_visit: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_proyect: Mapped[int] = mapped_column(Integer, ForeignKey("proyect.id_proyect"), nullable=False, index=True)
    # Nullable para las ordenes para llevar: no ocupan mesa. Una visita de
    # mesa siempre la trae (lo valida el servicio al crearla).
    id_restaurant_table: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("restaurant_table.id_restaurant_table"), nullable=True
    )
    id_restaurant_waiter: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("restaurant_waiter.id_restaurant_waiter"), nullable=True
    )
    service_type: Mapped[str] = mapped_column(String(20), nullable=False, default="mesa", index=True)
    customer_name: Mapped[str | None] = mapped_column(String(140), nullable=True)
    # Folio diario visible al cliente ("para llevar #7"). Se reinicia cada
    # dia por proyecto; solo aplica a para_llevar.
    daily_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    service_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    diners_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", index=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    table: Mapped[RestaurantTable | None] = relationship()
    orders: Mapped[list[RestaurantOrder]] = relationship(
        back_populates="visit", cascade="all, delete-orphan", order_by="RestaurantOrder.diner_index"
    )

    def serialize(self) -> dict:
        data = self.serialize_columns()
        data["table_number"] = self.table.number if self.table else None
        data["orders"] = [order.serialize() for order in self.orders]
        data["total"] = round(sum(order.total for order in self.orders), 2)
        return data


class RestaurantOrder(RestaurantRecord, Base):
    __tablename__ = "restaurant_order"

    id_restaurant_order: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_proyect: Mapped[int] = mapped_column(Integer, ForeignKey("proyect.id_proyect"), nullable=False, index=True)
    id_restaurant_visit: Mapped[int] = mapped_column(
        Integer, ForeignKey("restaurant_visit.id_restaurant_visit"), nullable=False, index=True
    )
    diner_index: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    id_restaurant_waiter: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("restaurant_waiter.id_restaurant_waiter"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="borrador", index=True)
    tip_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    tip_percent: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    tip_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    # Datos del cobro. Antes solo se marcaba status='pagado', sin registrar
    # con que se pago: el corte de caja daba por hecho que todo era efectivo.
    payment_method: Mapped[str | None] = mapped_column(String(20), nullable=True)
    received_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    # Solo con payment_method='mixto': la parte cubierta en efectivo. Es lo
    # unico que debe cuadrar contra el cajon en el corte.
    cash_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cooked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ready_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    visit: Mapped[RestaurantVisit] = relationship(back_populates="orders")
    items: Mapped[list[RestaurantOrderItem]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )

    @property
    def subtotal(self) -> float:
        return round(sum(item.line_total for item in self.items), 2)

    @property
    def total(self) -> float:
        return round(self.subtotal + float(self.tip_amount or 0), 2)

    @property
    def change_amount(self) -> float:
        """Cambio a devolver. Solo aplica si se capturo lo recibido.

        Se calcula contra la parte en EFECTIVO, no contra el total: en un
        pago mixto el cliente entrega billetes solo por esa parte, asi que
        comparar contra el total daba cambio cero cuando si habia que
        devolver dinero.
        """
        if self.received_amount is None:
            return 0.0
        return round(max(float(self.received_amount) - self.cash_portion, 0.0), 2)

    @property
    def cash_portion(self) -> float:
        """Parte del cobro que entra al cajon, para el corte de caja.

        'mixto' guarda explicitamente cuanto fue en efectivo; 'efectivo'
        cubre el total; tarjeta y transferencia no tocan el cajon.
        """
        if self.payment_method == "efectivo":
            return self.total
        if self.payment_method == "mixto":
            return round(float(self.cash_amount or 0), 2)
        if self.payment_method in ("tarjeta", "transferencia"):
            return 0.0
        # Cobros anteriores a que existiera payment_method: se asumen en
        # efectivo, que es como los contaba el corte antes de este cambio.
        return self.total if self.status == "pagado" else 0.0

    def serialize(self) -> dict:
        data = self.serialize_columns()
        data["items"] = [item.serialize() for item in self.items]
        data["subtotal"] = self.subtotal
        data["total"] = self.total
        data["change_amount"] = self.change_amount
        data["cash_portion"] = self.cash_portion
        data["table_number"] = self.visit.table.number if self.visit and self.visit.table else None
        return data


class RestaurantOrderItem(RestaurantRecord, Base):
    __tablename__ = "restaurant_order_item"

    id_restaurant_order_item: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_restaurant_order: Mapped[int] = mapped_column(
        Integer, ForeignKey("restaurant_order.id_restaurant_order"), nullable=False, index=True
    )
    id_restaurant_dish: Mapped[int] = mapped_column(
        Integer, ForeignKey("restaurant_dish.id_restaurant_dish"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    id_guisado_1: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("restaurant_guisado.id_restaurant_guisado"), nullable=True
    )
    id_guisado_2: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("restaurant_guisado.id_restaurant_guisado"), nullable=True
    )
    combinado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    order: Mapped[RestaurantOrder] = relationship(back_populates="items")
    dish: Mapped[RestaurantDish] = relationship()
    guisado_1: Mapped[RestaurantGuisado | None] = relationship(foreign_keys=[id_guisado_1])
    guisado_2: Mapped[RestaurantGuisado | None] = relationship(foreign_keys=[id_guisado_2])

    @property
    def line_total(self) -> float:
        return round((self.quantity or 0) * float(self.unit_price or 0), 2)

    def serialize(self) -> dict:
        data = self.serialize_columns()
        data["dish"] = self.dish.serialize() if self.dish else None
        data["guisado_1"] = self.guisado_1.serialize() if self.guisado_1 else None
        data["guisado_2"] = self.guisado_2.serialize() if self.guisado_2 else None
        data["line_total"] = self.line_total
        return data


class RestaurantReservation(RestaurantRecord, Base):
    __tablename__ = "restaurant_reservation"

    id_restaurant_reservation: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_proyect: Mapped[int] = mapped_column(Integer, ForeignKey("proyect.id_proyect"), nullable=False, index=True)
    id_restaurant_table: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("restaurant_table.id_restaurant_table"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(140), nullable=False)
    reservation_date: Mapped[date] = mapped_column(Date, nullable=False)
    reservation_time: Mapped[object] = mapped_column(Time, nullable=False)
    guests: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending")
    event_type: Mapped[str | None] = mapped_column(String(80), nullable=True)

    def serialize(self) -> dict:
        return self.serialize_columns()


class RestaurantInventoryItem(RestaurantRecord, Base):
    __tablename__ = "restaurant_inventory_item"

    id_restaurant_inventory_item: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_proyect: Mapped[int] = mapped_column(Integer, ForeignKey("proyect.id_proyect"), nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(160), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False, default=0)
    unit: Mapped[str] = mapped_column(String(40), nullable=False)
    cost_per_unit: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    # El producto del almacen que representa este insumo, y donde vive su
    # existencia. Nulos mientras nadie los empareje: un insumo sin enlace lleva
    # solo su saldo propio y no toca el nucleo, que es lo que permite adoptarlo
    # insumo por insumo. Ver `services/restaurant_inventory_bridge.py`.
    id_product: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("product.id_product"), nullable=True, index=True)
    id_location: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("location.id_location"), nullable=True)

    def serialize(self) -> dict:
        return self.serialize_columns()


class RestaurantInventoryMovement(RestaurantRecord, Base):
    """Ledger de existencias: toda alta, baja, merma o ajuste de stock.

    Antes restaurant_inventory_item.quantity se sobrescribia sin rastro, asi
    que no se podia auditar una merma ni reconstruir como se llego al saldo
    actual. Cada renglon guarda la cantidad antes y despues del movimiento,
    de modo que el saldo es verificable contra el historial.
    """

    __tablename__ = "restaurant_inventory_movement"

    id_restaurant_inventory_movement: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    id_proyect: Mapped[int] = mapped_column(Integer, ForeignKey("proyect.id_proyect"), nullable=False, index=True)
    id_restaurant_inventory_item: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("restaurant_inventory_item.id_restaurant_inventory_item"),
        nullable=False,
        index=True,
    )
    movement_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    previous_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    new_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit_cost: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    item: Mapped[RestaurantInventoryItem] = relationship()

    def serialize(self) -> dict:
        data = self.serialize_columns()
        data["item_description"] = self.item.description if self.item else None
        return data


class RestaurantRecipeItem(RestaurantRecord, Base):
    __tablename__ = "restaurant_recipe_item"

    id_restaurant_recipe_item: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_proyect: Mapped[int] = mapped_column(Integer, ForeignKey("proyect.id_proyect"), nullable=False, index=True)
    id_restaurant_dish: Mapped[int] = mapped_column(
        Integer, ForeignKey("restaurant_dish.id_restaurant_dish"), nullable=False
    )
    id_restaurant_inventory_item: Mapped[int] = mapped_column(
        Integer, ForeignKey("restaurant_inventory_item.id_restaurant_inventory_item"), nullable=False
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit: Mapped[str] = mapped_column(String(40), nullable=False)

    def serialize(self) -> dict:
        return self.serialize_columns()


class RestaurantCashSession(RestaurantRecord, Base):
    __tablename__ = "restaurant_cash_session"

    id_restaurant_cash_session: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_proyect: Mapped[int] = mapped_column(Integer, ForeignKey("proyect.id_proyect"), nullable=False, index=True)
    opened_by_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id_user"), nullable=False)
    opened_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    opening_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    closed_by_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("user.id_user"), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    closing_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    expected_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    difference: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open", index=True)

    def serialize(self) -> dict:
        return self.serialize_columns()
