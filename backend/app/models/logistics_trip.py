from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class LogisticsTrip(Base):
    __tablename__ = 'logistics_trip'
    __table_args__ = (
        CheckConstraint('planned_cost >= 0', name='ck_logistics_trip_planned_cost'),
        CheckConstraint('actual_cost >= 0', name='ck_logistics_trip_actual_cost'),
        CheckConstraint('revenue >= 0', name='ck_logistics_trip_revenue'),
        CheckConstraint('kilometers >= 0', name='ck_logistics_trip_kilometers'),
        CheckConstraint(
            "status IN ('solicitado', 'planeado', 'asignado', 'cargado', 'en tránsito', 'en ruta', 'retrasado', 'entregado', 'cerrado', 'facturado', 'cancelado')",
            name='ck_logistics_trip_status',
        ),
        CheckConstraint(
            'planned_delivery_at IS NULL OR planned_pickup_at IS NULL OR planned_delivery_at >= planned_pickup_at',
            name='ck_logistics_trip_planned_dates',
        ),
        CheckConstraint(
            'actual_delivery_at IS NULL OR actual_pickup_at IS NULL OR actual_delivery_at >= actual_pickup_at',
            name='ck_logistics_trip_actual_dates',
        ),
    )

    id_logistics_trip: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_logistics_service_request: Mapped[int] = mapped_column(
        ForeignKey('logistics_service_request.id_logistics_service_request'), nullable=False
    )
    id_customer_supplier: Mapped[int] = mapped_column(
        ForeignKey('customer_supplier.id_customer_supplier'), nullable=False
    )
    folio: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    id_logistics_unit: Mapped[int | None] = mapped_column(ForeignKey('logistics_unit.id_logistics_unit'), nullable=True)
    id_logistics_trailer: Mapped[int | None] = mapped_column(
        ForeignKey('logistics_trailer.id_logistics_trailer'), nullable=True
    )
    id_logistics_operator: Mapped[int | None] = mapped_column(
        ForeignKey('logistics_operator.id_logistics_operator'), nullable=True
    )
    id_logistics_file: Mapped[int | None] = mapped_column(ForeignKey('logistics_file.id_logistics_file'), nullable=True)
    supplier_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    route_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    expediente_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default='solicitado', server_default='solicitado')
    planned_pickup_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    planned_delivery_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    actual_pickup_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    actual_delivery_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    planned_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0, server_default='0')
    actual_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0, server_default='0')
    revenue: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0, server_default='0')
    kilometers: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0, server_default='0')
    restrictions: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey('user.id_user'), nullable=False)
    creation_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
    deletion_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {
            column.name: float(value) if isinstance(value, Decimal) else value.isoformat() if isinstance(value, datetime) else value
            for column in self.__table__.columns
            if (value := getattr(self, column.name)) is not None
        }

    def serialize_summary(self) -> dict:
        return {'id_logistics_trip': self.id_logistics_trip, 'folio': self.folio}