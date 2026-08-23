from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class LogisticsShipment(Base):
    __tablename__ = 'logistics_shipment'
    __table_args__ = (
        CheckConstraint(
            "status IN ('registrado', 'en tránsito', 'en aduana', 'liberado', 'entregado')",
            name='ck_logistics_shipment_status',
        ),
    )

    id_logistics_shipment: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_customer_supplier: Mapped[int] = mapped_column(
        ForeignKey('customer_supplier.id_customer_supplier'), nullable=False
    )
    shipment_number: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    bl_number: Mapped[str | None] = mapped_column(String(120), nullable=True)
    provider: Mapped[str | None] = mapped_column(String(180), nullable=True)
    transport_mode: Mapped[str | None] = mapped_column(String(60), nullable=True)
    cargo_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    origin_port: Mapped[str | None] = mapped_column(String(180), nullable=True)
    destination_port: Mapped[str | None] = mapped_column(String(180), nullable=True)
    customs: Mapped[str | None] = mapped_column(String(180), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default='registrado', server_default='registrado')
    tracking: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey('user.id_user'), nullable=False)
    creation_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {column.name: value.isoformat() if isinstance(value, datetime) else value for column in self.__table__.columns if (value := getattr(self, column.name)) is not None}

    def serialize_summary(self) -> dict:
        return {'id_logistics_shipment': self.id_logistics_shipment, 'shipment_number': self.shipment_number}