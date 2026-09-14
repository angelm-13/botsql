from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def to_json_value(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


class LogisticsMaintenance(Base):
    __tablename__ = 'logistics_maintenance'

    id_logistics_maintenance: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_logistics_unit: Mapped[int] = mapped_column(Integer, ForeignKey('logistics_unit.id_logistics_unit'), nullable=False)
    maintenance_type: Mapped[str] = mapped_column(String(80), nullable=False)
    scheduled_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    closed_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0, server_default='0')
    status: Mapped[str] = mapped_column(String(20), nullable=False, default='abierta', server_default='abierta')
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {column.name: to_json_value(getattr(self, column.name)) for column in self.__table__.columns}

    def serialize_summary(self) -> dict:
        return {'id_logistics_maintenance': self.id_logistics_maintenance, 'maintenance_type': self.maintenance_type}