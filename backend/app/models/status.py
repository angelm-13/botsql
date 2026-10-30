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


class Status(Base):
    __tablename__ = 'status'

    id_status: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    status_description: Mapped[object] = mapped_column(String(150), nullable=False)
    category: Mapped[object] = mapped_column(String(150), nullable=False)
    is_terminal: Mapped[bool] = mapped_column(Boolean, nullable=False)
    sort_order: Mapped[object] = mapped_column(Enum('desc', 'asc', name='status_sort_order_enum', native_enum=False, validate_strings=True, create_constraint=True), nullable=True)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {
            'id_status': to_json_value(self.id_status),
            'status_description': to_json_value(self.status_description),
            'category': to_json_value(self.category),
            'is_terminal': to_json_value(self.is_terminal),
            'sort_order': to_json_value(self.sort_order),
            'created_by': to_json_value(self.created_by),
            'creation_date': a_iso_utc(self.creation_date),
            'last_update_date': a_iso_utc(self.last_update_date),
            'deletion_date': a_iso_utc(self.deletion_date),
        }

    def serialize_summary(self) -> dict:
        return {'id_status': self.id_status}
