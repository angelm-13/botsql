from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class LogisticsLocation(Base):
    __tablename__ = 'logistics_location'
    __table_args__ = (
        UniqueConstraint('id_logistics_warehouse', 'code', name='uq_logistics_location_warehouse_code'),
        CheckConstraint('capacity >= 0', name='ck_logistics_location_capacity'),
        CheckConstraint("status IN ('activo', 'inactivo')", name='ck_logistics_location_status'),
    )

    id_logistics_location: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_logistics_warehouse: Mapped[int] = mapped_column(ForeignKey('logistics_warehouse.id_logistics_warehouse'), nullable=False)
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    zone: Mapped[str | None] = mapped_column(String(80), nullable=True)
    location_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    capacity: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0, server_default='0')
    status: Mapped[str] = mapped_column(String(20), nullable=False, default='activo', server_default='activo')
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {
            column.name: float(value) if isinstance(value, Decimal) else value.isoformat() if isinstance(value, datetime) else value
            for column in self.__table__.columns
            if (value := getattr(self, column.name)) is not None
        }

    def serialize_summary(self) -> dict:
        return {'id_logistics_location': self.id_logistics_location, 'code': self.code}