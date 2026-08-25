from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def to_json_value(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


class LogisticsContact(Base):
    __tablename__ = 'logistics_contact'

    id_logistics_contact: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_customer_supplier: Mapped[int] = mapped_column(Integer, ForeignKey('customer_supplier.id_customer_supplier'), nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    position: Mapped[str | None] = mapped_column(String(80), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default='activo', server_default='activo')
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {column.name: to_json_value(getattr(self, column.name)) for column in self.__table__.columns}

    def serialize_summary(self) -> dict:
        return {'id_logistics_contact': self.id_logistics_contact, 'full_name': self.full_name}