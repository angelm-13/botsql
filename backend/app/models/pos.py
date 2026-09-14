"""El punto de venta, ya dentro de la base de TYAKXA.

Que cambio
----------
El POS era otro proyecto contra otra base, y TYAKXA le hablaba por HTTP a
traves de `pos_gateway`/`pos_proxy`. Aqui sus tablas propias pasan a ser tablas
de esta base, y las que ya existian con otro nombre simplemente se comparten.

Lo que NO esta en este archivo es la mitad del trabajo: no hay `PosProduct`, ni
`PosUser`, ni `PosCustomer`, ni `PosCategory`. Un producto de la caja es
`Product`, un cliente del mostrador es `CustomerSupplier`, y la categoria es
`ProductFamily`. Esa ausencia es el punto: antes eran copias en otra base que
alguien tenia que emparejar a mano.

Las llaves
----------
Enteras, como todo TYAKXA. El POS usaba UUID, y mientras fueron dos bases daba
igual; al compartir tablas ya no, porque `PosSaleItem.id_product` apunta a
`product.id_product`, que es un entero. Ver la migracion
20260911100000 para por que se pudo empezar limpio en vez de convertir.

Los estados
-----------
Cadenas con CHECK en la base, no enum de Postgres, que es lo que usa el resto
de TYAKXA. Las listas validas viven aqui arriba como constantes para que el
servicio valide con lo mismo que la base exige, y no con una copia que se
desfasa.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    ARRAY, Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text,
    func, text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.models.base import Base

# JSONB en Postgres y JSON en SQLite, que es donde corre la suite. Sin esto los
# tres campos del corte de caja no se pueden declarar en un modelo que tiene que
# funcionar en los dos motores.
Json = JSONB().with_variant(JSON(), "sqlite")
# Lo mismo para los arreglos de enteros de una promocion.
IntArray = ARRAY(Integer).with_variant(JSON(), "sqlite")


# --- vocabulario --------------------------------------------------------
# Tienen que coincidir con los CHECK de la migracion 20260911100000.

ESTADOS_DE_TURNO = ("open", "closed_x", "closed_z")
TIPOS_DE_VENTA = ("dine_in", "takeout", "delivery", "online")
ESTADOS_DE_VENTA = ("open", "suspended", "paid", "cancelled", "refunded",
                    "partially_refunded")
ESTADOS_DE_COCINA = ("pending", "preparing", "ready", "served", "cancelled")
FORMAS_DE_PAGO = ("cash", "card", "transfer", "local_credit", "loyalty_points",
                  "delivery_platform")
REGLAS_DE_PROMOCION = ("percent_discount", "fixed_discount", "buy_x_get_y",
                       "nth_unit_free", "happy_hour", "bundle_price")
ESTADOS_DE_GASTO = ("recorded", "approved", "rejected")
TIPOS_DE_CREDITO = ("charge", "payment", "adjustment")
TIPOS_DE_LEALTAD = ("earn", "redeem", "expire", "adjustment")
ESTADOS_DE_COMPRA = ("draft", "sent", "partially_received", "received",
                     "cancelled")


def _valor(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)) or hasattr(value, "isoformat"):
        return value.isoformat()
    return value


class PosRecord:
    """Las cuatro columnas de auditoria que lleva toda tabla de TYAKXA.

    `created_by` sin llave foranea a proposito: es el mismo trato que le da
    `incident`, y una instalacion recien sembrada escribe filas antes de que
    exista el usuario 1.
    """

    created_by: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default=text("1"))
    creation_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def serialize_columns(self) -> dict:
        return {c.name: _valor(getattr(self, c.name)) for c in self.__table__.columns}

    def serialize(self) -> dict:
        return self.serialize_columns()


# --- la caja ------------------------------------------------------------

class PosCashSession(PosRecord, Base):
    """El turno de una caja: se abre con un fondo y se cierra con un corte."""

    __tablename__ = "pos_cash_session"

    id_pos_cash_session: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_proyect: Mapped[int] = mapped_column(Integer, ForeignKey("proyect.id_proyect"), nullable=False, index=True)
    register_name: Mapped[str] = mapped_column(String(120), nullable=False)
    id_user_opened: Mapped[int] = mapped_column(Integer, ForeignKey("user.id_user"), nullable=False)
    id_user_closed: Mapped[int | None] = mapped_column(Integer, ForeignKey("user.id_user"), nullable=True)
    opening_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0, server_default=text("0"))
    opened_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    session_status: Mapped[str] = mapped_column(String(20), nullable=False, default="open", server_default=text("'open'"))
    # Los tres y no solo la diferencia: sin lo declarado y lo esperado, un corte
    # con descuadre cero no distingue "cuadro" de "nadie conto".
    blind_declared_amounts: Mapped[dict | None] = mapped_column(Json, nullable=True)
    system_expected_amounts: Mapped[dict | None] = mapped_column(Json, nullable=True)
    discrepancy_amounts: Mapped[dict | None] = mapped_column(Json, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class PosCashWithdrawal(PosRecord, Base):
    """Un retiro de efectivo del turno, con quien lo autorizo."""

    __tablename__ = "pos_cash_withdrawal"

    id_pos_cash_withdrawal: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_proyect: Mapped[int] = mapped_column(Integer, ForeignKey("proyect.id_proyect"), nullable=False, index=True)
    id_pos_cash_session: Mapped[int] = mapped_column(
        Integer, ForeignKey("pos_cash_session.id_pos_cash_session"), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    reason: Mapped[str] = mapped_column(String(250), nullable=False)
    id_user_authorized: Mapped[int] = mapped_column(Integer, ForeignKey("user.id_user"), nullable=False)


# --- la venta -----------------------------------------------------------

class PosSale(PosRecord, Base):
    __tablename__ = "pos_sale"

    id_pos_sale: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_proyect: Mapped[int] = mapped_column(Integer, ForeignKey("proyect.id_proyect"), nullable=False, index=True)
    folio: Mapped[str] = mapped_column(String(40), nullable=False)
    sale_type: Mapped[str] = mapped_column(String(20), nullable=False, default="takeout", server_default=text("'takeout'"))
    sale_status: Mapped[str] = mapped_column(String(20), nullable=False, default="open", server_default=text("'open'"))
    table_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # El cliente del mostrador es el mismo renglon que el CRM y la facturacion
    # ven. Antes vivia en otra base, y por eso no aparecia en ninguno de los dos.
    id_customer_supplier: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("customer_supplier.id_customer_supplier"), nullable=True)
    id_user_waiter: Mapped[int | None] = mapped_column(Integer, ForeignKey("user.id_user"), nullable=True)
    id_user_cashier: Mapped[int | None] = mapped_column(Integer, ForeignKey("user.id_user"), nullable=True)
    id_pos_cash_session: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("pos_cash_session.id_pos_cash_session"), nullable=True, index=True)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0, server_default=text("0"))
    discount_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0, server_default=text("0"))
    tax_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0, server_default=text("0"))
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0, server_default=text("0"))
    # Copiado al vender, no consultado despues: el coste cambia con cada compra,
    # y un margen recalculado con el coste de hoy miente sobre la venta de ayer.
    total_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0, server_default=text("0"))
    delivery_platform: Mapped[str | None] = mapped_column(String(60), nullable=True)
    delivery_commission_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0, server_default=text("0"))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancelled_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # El CFDI de esta venta se emite desde el modulo de facturacion de TYAKXA.
    # El POS traia tablas `invoices` propias; no se absorbieron.
    id_invoice: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("invoice.id_invoice"), nullable=True)


class PosSaleItem(PosRecord, Base):
    """El renglon de una venta.

    `id_product` es el nudo de toda la integracion: apunta al producto del
    almacen. Antes apuntaba a `products.id` de la otra base, y por eso hacia
    falta `pos_product_link` para emparejar dos mundos.
    """

    __tablename__ = "pos_sale_item"

    id_pos_sale_item: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_proyect: Mapped[int] = mapped_column(Integer, ForeignKey("proyect.id_proyect"), nullable=False, index=True)
    id_pos_sale: Mapped[int] = mapped_column(Integer, ForeignKey("pos_sale.id_pos_sale"), nullable=False, index=True)
    id_product: Mapped[int] = mapped_column(Integer, ForeignKey("product.id_product"), nullable=False, index=True)
    id_pos_product_variant: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("pos_product_variant.id_pos_product_variant"), nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0, server_default=text("0"))
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0, server_default=text("0"))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0, server_default=text("0"))
    line_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0, server_default=text("0"))
    id_pos_promotion: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("pos_promotion.id_pos_promotion"), nullable=True)
    kitchen_zone: Mapped[str | None] = mapped_column(String(60), nullable=True)
    kitchen_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", server_default=text("'pending'"))
    special_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)


class PosPayment(PosRecord, Base):
    """Un pago de la venta. Son varios porque una venta se puede partir."""

    __tablename__ = "pos_payment"

    id_pos_payment: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_proyect: Mapped[int] = mapped_column(Integer, ForeignKey("proyect.id_proyect"), nullable=False, index=True)
    id_pos_sale: Mapped[int] = mapped_column(Integer, ForeignKey("pos_sale.id_pos_sale"), nullable=False, index=True)
    payment_method: Mapped[str] = mapped_column(String(30), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    tendered_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    change_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0, server_default=text("0"))
    reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    id_user_received: Mapped[int] = mapped_column(Integer, ForeignKey("user.id_user"), nullable=False)


# --- variantes ----------------------------------------------------------

class PosProductVariant(PosRecord, Base):
    """Una talla o un color del mismo producto.

    No trae `current_stock`, que el POS si tenia: la existencia de una variante
    es existencia del almacen, y guardarla aqui volveria a crear las dos
    respuestas a "cuanto hay" que esta integracion existe para eliminar.
    """

    __tablename__ = "pos_product_variant"

    id_pos_product_variant: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_proyect: Mapped[int] = mapped_column(Integer, ForeignKey("proyect.id_proyect"), nullable=False, index=True)
    id_product: Mapped[int] = mapped_column(Integer, ForeignKey("product.id_product"), nullable=False, index=True)
    sku: Mapped[str | None] = mapped_column(String(60), nullable=True)
    barcode: Mapped[str | None] = mapped_column(String(60), nullable=True)
    attributes: Mapped[dict | None] = mapped_column(Json, nullable=True)
    price_delta: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0, server_default=text("0"))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))


# --- promociones --------------------------------------------------------

class PosPromotion(PosRecord, Base):
    __tablename__ = "pos_promotion"

    id_pos_promotion: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_proyect: Mapped[int] = mapped_column(Integer, ForeignKey("proyect.id_proyect"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(30), nullable=False)
    config: Mapped[dict | None] = mapped_column(Json, nullable=True)
    applicable_product_ids: Mapped[list | None] = mapped_column(IntArray, nullable=True)
    applicable_family_ids: Mapped[list | None] = mapped_column(IntArray, nullable=True)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    requires_stock: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    max_uses_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_uses_per_customer: Mapped[int | None] = mapped_column(Integer, nullable=True)
    times_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    is_stackable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))


class PosPromotionRedemption(PosRecord, Base):
    __tablename__ = "pos_promotion_redemption"

    id_pos_promotion_redemption: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_proyect: Mapped[int] = mapped_column(Integer, ForeignKey("proyect.id_proyect"), nullable=False, index=True)
    id_pos_promotion: Mapped[int] = mapped_column(
        Integer, ForeignKey("pos_promotion.id_pos_promotion"), nullable=False, index=True)
    id_pos_sale: Mapped[int] = mapped_column(Integer, ForeignKey("pos_sale.id_pos_sale"), nullable=False)
    id_customer_supplier: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("customer_supplier.id_customer_supplier"), nullable=True)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0, server_default=text("0"))


# --- gastos -------------------------------------------------------------

class PosExpenseCategory(PosRecord, Base):
    __tablename__ = "pos_expense_category"

    id_pos_expense_category: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_proyect: Mapped[int] = mapped_column(Integer, ForeignKey("proyect.id_proyect"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    is_payroll: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))


class PosExpense(PosRecord, Base):
    __tablename__ = "pos_expense"

    id_pos_expense: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_proyect: Mapped[int] = mapped_column(Integer, ForeignKey("proyect.id_proyect"), nullable=False, index=True)
    id_pos_expense_category: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("pos_expense_category.id_pos_expense_category"), nullable=True)
    description: Mapped[str] = mapped_column(String(250), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    # El proveedor al que se le pago es un `customer_supplier`, igual que el
    # cliente: el POS tenia `suppliers` y `customers` por separado y las dos
    # eran lo mismo que esta tabla.
    id_customer_supplier: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("customer_supplier.id_customer_supplier"), nullable=True)
    receipt_url: Mapped[str | None] = mapped_column(String(400), nullable=True)
    expense_status: Mapped[str] = mapped_column(String(20), nullable=False, default="recorded", server_default=text("'recorded'"))
    id_pos_cash_session: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("pos_cash_session.id_pos_cash_session"), nullable=True)
    expense_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


# --- credito del cliente ------------------------------------------------

class PosCreditAccount(PosRecord, Base):
    __tablename__ = "pos_credit_account"

    id_pos_credit_account: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_proyect: Mapped[int] = mapped_column(Integer, ForeignKey("proyect.id_proyect"), nullable=False, index=True)
    id_customer_supplier: Mapped[int] = mapped_column(
        Integer, ForeignKey("customer_supplier.id_customer_supplier"), nullable=False)
    credit_limit: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0, server_default=text("0"))
    current_balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0, server_default=text("0"))
    payment_due_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))


class PosCreditMovement(PosRecord, Base):
    """Cada cargo o abono del fiado.

    `balance_after` se guarda y no se recalcula, por la misma razon que el libro
    del restaurante: un saldo recalculado hoy no prueba cual era el saldo el dia
    que se fio.
    """

    __tablename__ = "pos_credit_movement"

    id_pos_credit_movement: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_proyect: Mapped[int] = mapped_column(Integer, ForeignKey("proyect.id_proyect"), nullable=False, index=True)
    id_pos_credit_account: Mapped[int] = mapped_column(
        Integer, ForeignKey("pos_credit_account.id_pos_credit_account"), nullable=False, index=True)
    movement_type: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    balance_after: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0, server_default=text("0"))
    id_pos_sale: Mapped[int | None] = mapped_column(Integer, ForeignKey("pos_sale.id_pos_sale"), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


# --- lealtad ------------------------------------------------------------

class PosLoyaltyAccount(PosRecord, Base):
    __tablename__ = "pos_loyalty_account"

    id_pos_loyalty_account: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_proyect: Mapped[int] = mapped_column(Integer, ForeignKey("proyect.id_proyect"), nullable=False, index=True)
    id_customer_supplier: Mapped[int] = mapped_column(
        Integer, ForeignKey("customer_supplier.id_customer_supplier"), nullable=False)
    points_balance: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    tier: Mapped[str | None] = mapped_column(String(40), nullable=True)


class PosLoyaltyMovement(PosRecord, Base):
    __tablename__ = "pos_loyalty_movement"

    id_pos_loyalty_movement: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_proyect: Mapped[int] = mapped_column(Integer, ForeignKey("proyect.id_proyect"), nullable=False, index=True)
    id_pos_loyalty_account: Mapped[int] = mapped_column(
        Integer, ForeignKey("pos_loyalty_account.id_pos_loyalty_account"), nullable=False, index=True)
    movement_type: Mapped[str] = mapped_column(String(20), nullable=False)
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    id_pos_sale: Mapped[int | None] = mapped_column(Integer, ForeignKey("pos_sale.id_pos_sale"), nullable=True)


# --- compras ------------------------------------------------------------

class PosPurchaseOrder(PosRecord, Base):
    __tablename__ = "pos_purchase_order"

    id_pos_purchase_order: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_proyect: Mapped[int] = mapped_column(Integer, ForeignKey("proyect.id_proyect"), nullable=False, index=True)
    folio: Mapped[str] = mapped_column(String(40), nullable=False)
    id_customer_supplier: Mapped[int] = mapped_column(
        Integer, ForeignKey("customer_supplier.id_customer_supplier"), nullable=False)
    # La bodega es una `location` del nucleo. El POS tenia `warehouses` propias.
    id_location: Mapped[int | None] = mapped_column(Integer, ForeignKey("location.id_location"), nullable=True)
    order_status: Mapped[str] = mapped_column(String(24), nullable=False, default="draft", server_default=text("'draft'"))
    expected_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class PosPurchaseOrderItem(PosRecord, Base):
    __tablename__ = "pos_purchase_order_item"

    id_pos_purchase_order_item: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_proyect: Mapped[int] = mapped_column(Integer, ForeignKey("proyect.id_proyect"), nullable=False, index=True)
    id_pos_purchase_order: Mapped[int] = mapped_column(
        Integer, ForeignKey("pos_purchase_order.id_pos_purchase_order"), nullable=False, index=True)
    id_product: Mapped[int] = mapped_column(Integer, ForeignKey("product.id_product"), nullable=False)
    quantity_ordered: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    quantity_received: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False, default=0, server_default=text("0"))
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0, server_default=text("0"))
