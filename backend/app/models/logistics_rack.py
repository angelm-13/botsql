from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class LogisticsRack(Base):
    __tablename__ = 'logistics_rack'
    __table_args__ = (
        CheckConstraint('quantity >= 0', name='ck_logistics_rack_quantity'),
        CheckConstraint(
            "status IN ('en_cliente', 'en_almacen', 'pendiente_retorno', 'en_reparacion')",
            name='ck_logistics_rack_status',
        ),
        CheckConstraint("condition IN ('bueno', 'regular', 'dañado')", name='ck_logistics_rack_condition'),
    )

    id_logistics_rack: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_customer_supplier: Mapped[int] = mapped_column(ForeignKey('customer_supplier.id_customer_supplier'), nullable=False)
    id_logistics_location: Mapped[int] = mapped_column(ForeignKey('logistics_location.id_logistics_location'), nullable=False)
    code: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default='en_cliente', server_default='en_cliente')
    condition: Mapped[str] = mapped_column(String(20), nullable=False, default='bueno', server_default='bueno')
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default='1')
    sent_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    received_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {
            column.name: value.isoformat() if isinstance(value, (datetime, date)) else value
            for column in self.__table__.columns
            if (value := getattr(self, column.name)) is not None
        }

    def serialize_summary(self) -> dict:
        return {'id_logistics_rack': self.id_logistics_rack, 'code': self.code}