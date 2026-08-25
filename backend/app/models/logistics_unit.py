from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def to_json_value(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


class LogisticsUnit(Base):
    __tablename__ = 'logistics_unit'

    id_logistics_unit: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plate: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    unit_type: Mapped[str] = mapped_column(String(80), nullable=False)
    mileage: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0, server_default='0')
    availability_status: Mapped[str] = mapped_column(String(30), nullable=False, default='disponible', server_default='disponible')
    insurance_expiration: Mapped[date | None] = mapped_column(Date, nullable=True)
    verification_expiration: Mapped[date | None] = mapped_column(Date, nullable=True)
    policy_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    fuel_efficiency: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default='activo', server_default='activo')
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {column.name: to_json_value(getattr(self, column.name)) for column in self.__table__.columns}

    def serialize_summary(self) -> dict:
        return {'id_logistics_unit': self.id_logistics_unit, 'plate': self.plate}