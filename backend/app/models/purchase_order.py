"""La orden de compra: lo que Compras compra, con la evidencia de que se compro.

Por que no basta un "comprado"
------------------------------
Una compra que solo se marca como hecha no demuestra nada: ni que se hizo, ni por
cuanto, ni a quien. Aqui comprar es registrar una ORDEN con proveedor, folio, monto,
forma de pago y comprobante, y cada paso -cotizar, autorizar, comprar, recibir- lo
da una persona distinta y deja renglon en la bitacora (`purchase_event`).

El software no prueba que el dinero se gasto bien: hace que hacerlo mal sea dificil
y que se note. Lo que protege es, en este orden:

* el comprobante es obligatorio para comprar;
* un comprobante no puede justificar dos ordenes (la misma huella de archivo, el mismo
  folio del mismo proveedor, el mismo UUID de CFDI);
* quien compra no autoriza, y quien compra no recibe;
* nada se edita en silencio: cada cambio de estado queda con quien y cuando.

Una orden, varios proyectos
---------------------------
Una compra real puede surtir a varios proyectos (100 costales de cemento: 40 a la obra
A, 35 a la B, 25 a la C). Por eso el comprobante pertenece a UNA orden, y la orden
reparte sus renglones por proyecto (`purchase_order_line.id_proyect`). Lo que se
prohibe es usar el mismo comprobante en dos ordenes distintas -contar el mismo dinero
dos veces-, no que una orden cubra varias obras.

Los montos de autorizacion no estan en el codigo
------------------------------------------------
`purchase_policy` es una sola fila que se edita sin tocar nada: desde que monto la
orden necesita autorizacion previa y desde cual la compra la hace quien autoriza.
Por omision todo se autoriza y nadie compra por su cuenta: es facil aflojarlo despues
y dificil apretarlo cuando ya hubo un problema.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean, CheckConstraint, Date, DateTime, ForeignKey, Integer, Numeric, String, Text,
    func, text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

ORDER_STATUSES = (
    "draft", "pending_authorization", "authorized", "rejected", "purchased",
    "partially_received", "received", "closed", "cancelled",
)
PAYMENT_METHODS = ("cash", "transfer", "card", "credit", "check", "other")
VOUCHER_KINDS = ("quote", "invoice", "receipt", "payment_proof")


def _valor(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


class _Serializable:
    def serialize(self) -> dict:
        return {c.name: _valor(getattr(self, c.name)) for c in self.__table__.columns}


class PurchaseOrder(_Serializable, Base):
    __tablename__ = "purchase_order"
    __table_args__ = (
        CheckConstraint(
            "order_status IN ('draft', 'pending_authorization', 'authorized', 'rejected', "
            "'purchased', 'partially_received', 'received', 'closed', 'cancelled')",
            name="ck_purchase_order_status",
        ),
        CheckConstraint(
            "payment_method IS NULL OR payment_method IN "
            "('cash', 'transfer', 'card', 'credit', 'check', 'other')",
            name="ck_purchase_order_payment_method",
        ),
    )

    id_purchase_order: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # El numero con el que se conoce la orden: OC-2026-00012.
    folio: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    id_customer_supplier: Mapped[int] = mapped_column(
        Integer, ForeignKey("customer_supplier.id_customer_supplier"), nullable=False, index=True)
    order_status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="draft", server_default=text("'draft'"))
    description: Mapped[str | None] = mapped_column(String(300), nullable=True)
    expected_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Tres cifras distintas, a proposito: lo cotizado, lo autorizado y lo comprobado.
    # Si la factura sale mas cara de lo autorizado, la diferencia es la alarma.
    quoted_total: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    authorized_total: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    total_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="MXN", server_default=text("'MXN'"))

    # Lo que decidio la politica al enviar la orden. Se guarda en la orden y no se
    # recalcula: cambiar los montos despues no reescribe lo que ya se autorizo.
    requires_authorization: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true"))
    requires_manager_purchase: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false"))
    authorized_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    authorized_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    authorization_note: Mapped[str | None] = mapped_column(String(300), nullable=True)

    # La evidencia de la compra.
    purchase_folio: Mapped[str | None] = mapped_column(String(60), nullable=True)
    purchase_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    payment_method: Mapped[str | None] = mapped_column(String(20), nullable=True)
    payment_reference: Mapped[str | None] = mapped_column(String(80), nullable=True)
    # "Pago externo": se pago fuera del sistema y aqui solo queda el registro.
    paid_externally: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false"))
    purchased_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    purchased_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_by: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default=text("1"))
    creation_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class PurchaseOrderLine(_Serializable, Base):
    __tablename__ = "purchase_order_line"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_purchase_order_line_quantity"),
        CheckConstraint("quantity_received >= 0", name="ck_purchase_order_line_received"),
    )

    id_purchase_order_line: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True)
    id_purchase_order: Mapped[int] = mapped_column(
        Integer, ForeignKey("purchase_order.id_purchase_order"), nullable=False, index=True)
    # Que necesidad de que proyecto cubre este renglon. Vacia si Compras agrego algo
    # por su cuenta.
    id_proyect_material_need: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("proyect_material_need.id_proyect_material_need"), nullable=True)
    id_proyect: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("proyect.id_proyect"), nullable=True, index=True)
    id_material: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("material.id_material"), nullable=True)
    description: Mapped[str] = mapped_column(String(200), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(40), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_cost: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    quantity_received: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0"))
    created_by: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default=text("1"))
    creation_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class PurchaseVoucher(_Serializable, Base):
    """Un comprobante: la cotizacion, la factura, el ticket o el comprobante de pago.

    La huella del archivo, el folio por proveedor y el UUID del CFDI son unicos en
    TODA la base (ver los indices de la migracion): el mismo papel no justifica dos
    compras.
    """
    __tablename__ = "purchase_voucher"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('quote', 'invoice', 'receipt', 'payment_proof')",
            name="ck_purchase_voucher_kind",
        ),
    )

    id_purchase_voucher: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True)
    id_purchase_order: Mapped[int] = mapped_column(
        Integer, ForeignKey("purchase_order.id_purchase_order"), nullable=False, index=True)
    # Del proveedor de la orden, copiado: el folio es unico POR PROVEEDOR.
    id_customer_supplier: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(14), nullable=False)
    folio: Mapped[str | None] = mapped_column(String(60), nullable=True)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    extension: Mapped[str] = mapped_column(String(10), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    file_path: Mapped[str] = mapped_column(
        String(500), nullable=False, default="", server_default=text("''"))
    # Si el comprobante es un CFDI, lo que dice el propio archivo, no lo que tecleo
    # el comprador.
    cfdi_uuid: Mapped[str | None] = mapped_column(String(40), nullable=True)
    rfc_emisor: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_by: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default=text("1"))
    creation_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now())
    deletion_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        datos = {c.name: _valor(getattr(self, c.name)) for c in self.__table__.columns}
        # La ruta en disco no sale de aqui: el archivo se pide por su endpoint.
        datos.pop("file_path", None)
        return datos


class PurchaseEvent(_Serializable, Base):
    """La bitacora de una orden: quien hizo que, cuando, y desde que estado.

    Solo se agrega, nunca se edita ni se borra. Cambiar el monto o el folio de una
    compra ya registrada queda aqui como un movimiento.
    """
    __tablename__ = "purchase_event"

    id_purchase_event: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True)
    id_purchase_order: Mapped[int] = mapped_column(
        Integer, ForeignKey("purchase_order.id_purchase_order"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(24), nullable=True)
    to_status: Mapped[str | None] = mapped_column(String(24), nullable=True)
    note: Mapped[str | None] = mapped_column(String(300), nullable=True)
    # Lo que cambio, como texto JSON ("monto: 18000 -> 19500"). Texto y no JSONB para
    # que corra igual en las pruebas.
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now())


class PurchasePolicy(_Serializable, Base):
    """Los montos de autorizacion. Una sola fila (`id_purchase_policy = 1`)."""
    __tablename__ = "purchase_policy"

    id_purchase_policy: Mapped[int] = mapped_column(Integer, primary_key=True)
    # La orden que cotice mas de esto necesita autorizacion ANTES de comprar. En 0,
    # que es el valor por omision, toda orden se autoriza.
    authorize_above: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=0, server_default=text("0"))
    # La orden que cotice mas de esto la compra quien autoriza, no Compras. Vacio =
    # nunca: es lo que viene por omision.
    manager_buys_above: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    # Cuanto puede salir la factura por encima de lo autorizado antes de volver a
    # pedir autorizacion.
    overrun_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=10, server_default=text("10"))
    updated_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_update_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
