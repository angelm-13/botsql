from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class LogisticsServiceRequest(Base):
    __tablename__ = 'logistics_service_request'
    __table_args__ = (
        CheckConstraint(
            "status IN ('solicitado', 'aprobado', 'programado', 'cancelado')",
            name='ck_logistics_service_request_status',
        ),
        CheckConstraint(
            "priority IN ('baja', 'normal', 'alta', 'urgente')",
            name='ck_logistics_service_request_priority',
        ),
        CheckConstraint(
            'requested_delivery_at IS NULL OR requested_pickup_at IS NULL OR requested_delivery_at >= requested_pickup_at',
            name='ck_logistics_service_request_dates',
        ),
    )

    id_logistics_service_request: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_customer_supplier: Mapped[int] = mapped_column(
        ForeignKey('customer_supplier.id_customer_supplier'), nullable=False
    )
    id_logistics_quotation: Mapped[int | None] = mapped_column(
        ForeignKey('logistics_quotation.id_logistics_quotation'), nullable=True
    )
    request_number: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    request_type: Mapped[str] = mapped_column(String(100), nullable=False)
    origin: Mapped[str | None] = mapped_column(Text, nullable=True)
    destination: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_pickup_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    requested_delivery_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default='solicitado', server_default='solicitado')
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default='normal', server_default='normal')
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey('user.id_user'), nullable=False)
    creation_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
    deletion_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {
            column.name: value.isoformat() if isinstance(value, datetime) else value
            for column in self.__table__.columns
            if (value := getattr(self, column.name)) is not None
        }

    def serialize_summary(self) -> dict:
        return {'id_logistics_service_request': self.id_logistics_service_request, 'request_number': self.request_number}