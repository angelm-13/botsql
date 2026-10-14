from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.utils.tiempo import a_iso_utc


class InvoicePayment(Base):
    """Un abono a una factura de pago en parcialidades o diferido.

    Cuando el metodo de pago es PPD, la factura no acredita el cobro: cada
    abono exige su propio comprobante, de tipo P, con el complemento de pagos.
    Ese comprobante tiene la particularidad de ir en ceros -SubTotal y Total
    valen cero- porque el importe vive dentro del complemento, no en el cuerpo.

    Cada renglon guarda lo que el SAT pide del documento relacionado: el folio
    fiscal de la factura, el numero de parcialidad, el saldo que habia antes,
    lo que se paga y el saldo que queda. Ese encadenamiento es lo que permite
    reconstruir el estado de cuenta y lo que hace que un abono no se pueda
    registrar dos veces con distinto saldo.
    """

    __tablename__ = "invoice_payment"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_invoice_payment_idempotency_key"),
        UniqueConstraint("id_invoice", "instalment", name="uq_invoice_payment_instalment"),
        CheckConstraint("amount > 0", name="ck_invoice_payment_amount_positive"),
        CheckConstraint("previous_balance >= 0", name="ck_invoice_payment_previous_balance"),
        CheckConstraint("outstanding_balance >= 0", name="ck_invoice_payment_outstanding"),
        Index("ix_invoice_payment_invoice", "id_invoice", "instalment"),
    )

    id_invoice_payment: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # La factura que se esta abonando.
    id_invoice: Mapped[int] = mapped_column(ForeignKey("invoice.id_invoice"), nullable=False)
    id_proyect: Mapped[int] = mapped_column(ForeignKey("proyect.id_proyect"), nullable=False)
    # El comprobante de tipo P que ampara este abono. Se crea al timbrarlo.
    id_payment_invoice: Mapped[int | None] = mapped_column(ForeignKey("invoice.id_invoice"), nullable=True)

    paid_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    # c_FormaPago del abono, que puede diferir de la de la factura.
    payment_form: Mapped[str] = mapped_column(String(2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="MXN", server_default="MXN")
    exchange_rate: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, default=1, server_default="1")

    # Numero de parcialidad, empezando en 1.
    instalment: Mapped[int] = mapped_column(Integer, nullable=False)
    previous_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    outstanding_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)

    operation_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    note: Mapped[str | None] = mapped_column(String(300), nullable=True)

    # pendiente -> timbrado | cancelado
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pendiente", server_default="pendiente")
    stamp_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False)

    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
    deletion_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def serialize(self):
        def numero(valor):
            return format(valor, "f") if valor is not None else None

        return {
            "id_invoice_payment": self.id_invoice_payment,
            "id_invoice": self.id_invoice,
            "id_proyect": self.id_proyect,
            "id_payment_invoice": self.id_payment_invoice,
            "paid_at": self.paid_at.isoformat() if self.paid_at else None,
            "payment_form": self.payment_form,
            "currency": self.currency,
            "exchange_rate": numero(self.exchange_rate),
            "instalment": self.instalment,
            "previous_balance": numero(self.previous_balance),
            "amount": numero(self.amount),
            "outstanding_balance": numero(self.outstanding_balance),
            "operation_number": self.operation_number,
            "note": self.note,
            "status": self.status,
            "stamp_metadata": self.stamp_metadata,
            "idempotency_key": self.idempotency_key,
            "created_by": self.created_by,
            "creation_date": a_iso_utc(self.creation_date),
        }
