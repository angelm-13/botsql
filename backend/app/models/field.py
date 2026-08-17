from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, BigInteger, SmallInteger, Boolean, Date, DateTime, Float, Numeric, ForeignKey, Text, JSON, Enum, LargeBinary, UniqueConstraint, func
from app.models.base import Base


def to_json_value(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.hex()
    return value


class Field(Base):
    __tablename__ = 'field'

    id_field: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)
    table_name: Mapped[object] = mapped_column(String(50), nullable=False)
    field_name: Mapped[object] = mapped_column(String(50), nullable=False)

    def serialize(self) -> dict:
        return {
            'id_field': to_json_value(self.id_field),
            'created_by': to_json_value(self.created_by),
            'creation_date': to_json_value(self.creation_date),
            'last_update_date': to_json_value(self.last_update_date),
            'deletion_date': to_json_value(self.deletion_date),
            'table_name': to_json_value(self.table_name),
            'field_name': to_json_value(self.field_name),
        }

    def serialize_summary(self) -> dict:
        return {'id_field': self.id_field}
