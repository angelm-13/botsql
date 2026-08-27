from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, BigInteger, SmallInteger, Boolean, Date, DateTime, Float, Numeric, ForeignKey, Text, JSON, Enum, LargeBinary, UniqueConstraint, func, text
from app.models.base import Base


def to_json_value(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.hex()
    return value


class LocationType(Base):
    __tablename__ = 'location_type'

    id_location_type: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    location_type_description: Mapped[object] = mapped_column(String(200), nullable=False)
    # Las ubicaciones de este tipo son almacenes: la raiz del arbol.
    is_warehouse: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text('0'), default=False)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {
            'id_location_type': to_json_value(self.id_location_type),
            'location_type_description': to_json_value(self.location_type_description),
            'is_warehouse': to_json_value(self.is_warehouse),
            'created_by': to_json_value(self.created_by),
            'creation_date': to_json_value(self.creation_date),
            'last_update_date': to_json_value(self.last_update_date),
            'deletion_date': to_json_value(self.deletion_date),
        }

    def serialize_summary(self) -> dict:
        return {'id_location_type': self.id_location_type}
