from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, BigInteger, SmallInteger, Boolean, Date, DateTime, Float, Numeric, ForeignKey, Text, JSON, Enum, LargeBinary, UniqueConstraint, func
from app.models.base import Base
from app.utils.tiempo import a_iso_utc


def to_json_value(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.hex()
    return value


class Unit(Base):
    __tablename__ = 'unit'

    id_unit: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    unit_code: Mapped[object] = mapped_column(String(20), nullable=True)
    unit_name: Mapped[object] = mapped_column(String(100), nullable=False)
    unit_category: Mapped[object] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    symbol: Mapped[object] = mapped_column(String(20), nullable=True)
    measurement_system: Mapped[object] = mapped_column(Enum('metric', 'imperial', 'mixed', name='unit_measurement_system_enum', native_enum=False, validate_strings=True, create_constraint=True), nullable=False)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {
            'id_unit': to_json_value(self.id_unit),
            'unit_code': to_json_value(self.unit_code),
            'unit_name': to_json_value(self.unit_name),
            'unit_category': to_json_value(self.unit_category),
            'is_active': to_json_value(self.is_active),
            'symbol': to_json_value(self.symbol),
            'measurement_system': to_json_value(self.measurement_system),
            'created_by': to_json_value(self.created_by),
            'creation_date': a_iso_utc(self.creation_date),
            'last_update_date': a_iso_utc(self.last_update_date),
            'deletion_date': a_iso_utc(self.deletion_date),
        }

    def serialize_summary(self) -> dict:
        return {'id_unit': self.id_unit}
