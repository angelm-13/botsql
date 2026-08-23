from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class LogisticsReceivable(Base):
    __tablename__ = 'logistics_receivable'
    __table_args__ = (
        CheckConstraint('amount >= 0', name='ck_logistics_receivable_amount'),
        CheckConstraint("status IN ('pendiente', 'pagado', 'vencido')", name='ck_logistics_receivable_status'),
    )

    id_logistics_receivable: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_invoice: Mapped[int] = mapped_column(ForeignKey('invoice.id_invoice'), nullable=False)
    id_customer_supplier: Mapped[int] = mapped_column(ForeignKey('customer_supplier.id_customer_supplier'), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    due_at: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default='pendiente', server_default='pendiente')
    paid_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey('user.id_user'), nullable=False)
    creation_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {column.name: float(value) if isinstance(value, Decimal) else value.isoformat() if isinstance(value, (date, datetime)) else value for column in self.__table__.columns if (value := getattr(self, column.name)) is not None}

    def serialize_summary(self) -> dict:
        return {'id_logistics_receivable': self.id_logistics_receivable, 'id_invoice': self.id_invoice}