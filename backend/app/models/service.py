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


class Service(Base):
    __tablename__ = 'service'

    id_service: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    service_description: Mapped[object] = mapped_column(String(500), nullable=False)
    average_time_cost: Mapped[float] = mapped_column(Numeric(10,2), nullable=True)
    id_brand: Mapped[int] = mapped_column(Integer, ForeignKey('brand.id_brand'), nullable=False)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {
            'id_service': to_json_value(self.id_service),
            'service_description': to_json_value(self.service_description),
            'average_time_cost': to_json_value(self.average_time_cost),
            'id_brand': to_json_value(self.id_brand),
            'created_by': to_json_value(self.created_by),
            'creation_date': a_iso_utc(self.creation_date),
            'last_update_date': a_iso_utc(self.last_update_date),
            'deletion_date': a_iso_utc(self.deletion_date),
        }

    def serialize_summary(self) -> dict:
        return {'id_service': self.id_service}
