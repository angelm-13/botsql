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


class Proyect(Base):
    __tablename__ = 'proyect'

    id_proyect: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    id_customer_supplier: Mapped[int] = mapped_column(Integer, ForeignKey('customer_supplier.id_customer_supplier'), nullable=False)
    leader: Mapped[int] = mapped_column(Integer, ForeignKey('user.id_user'), nullable=False)
    proyect_description: Mapped[object] = mapped_column(String(200), nullable=False)
    title: Mapped[object] = mapped_column(String(50), nullable=True)
    proyect_status: Mapped[object] = mapped_column(String(20), nullable=False, default='draft', server_default=text("'draft'"))
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey('user.id_user'), nullable=False)
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {
            'id_proyect': to_json_value(self.id_proyect),
            'id_customer_supplier': to_json_value(self.id_customer_supplier),
            'leader': to_json_value(self.leader),
            'proyect_description': to_json_value(self.proyect_description),
            'title': to_json_value(self.title),
            'proyect_status': to_json_value(self.proyect_status),
            'created_by': to_json_value(self.created_by),
            'creation_date': to_json_value(self.creation_date),
            'last_update_date': to_json_value(self.last_update_date),
            'deletion_date': to_json_value(self.deletion_date),
        }

    def serialize_summary(self) -> dict:
        return {'id_proyect': self.id_proyect}
