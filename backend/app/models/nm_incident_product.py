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


class NmIncidentProduct(Base):
    __tablename__ = 'nm_incident_product'

    id_nm_incident_product: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    id_incident: Mapped[int] = mapped_column(Integer, ForeignKey('incident.id_incident'), nullable=False)
    id_product: Mapped[int] = mapped_column(Integer, ForeignKey('product.id_product'), nullable=False)
    note: Mapped[object] = mapped_column(String(300), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    close_date: Mapped[object] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {
            'id_nm_incident_product': to_json_value(self.id_nm_incident_product),
            'id_incident': to_json_value(self.id_incident),
            'id_product': to_json_value(self.id_product),
            'note': to_json_value(self.note),
            'quantity': to_json_value(self.quantity),
            'close_date': to_json_value(self.close_date),
            'created_by': to_json_value(self.created_by),
            'creation_date': to_json_value(self.creation_date),
            'last_update_date': to_json_value(self.last_update_date),
            'deletion_date': to_json_value(self.deletion_date),
        }

    def serialize_summary(self) -> dict:
        return {'id_nm_incident_product': self.id_nm_incident_product}
