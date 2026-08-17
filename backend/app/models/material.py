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


class Material(Base):
    __tablename__ = 'material'

    id_material: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    material_description: Mapped[object] = mapped_column(String(200), nullable=False)
    id_unit: Mapped[int] = mapped_column(Integer, ForeignKey('unit.id_unit'), nullable=False)
    id_brand: Mapped[int] = mapped_column(Integer, ForeignKey('brand.id_brand'), nullable=False)
    id_product_family: Mapped[int] = mapped_column(Integer, ForeignKey('product_family.id_product_family'), nullable=False)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {
            'id_material': to_json_value(self.id_material),
            'material_description': to_json_value(self.material_description),
            'id_unit': to_json_value(self.id_unit),
            'id_brand': to_json_value(self.id_brand),
            'id_product_family': to_json_value(self.id_product_family),
            'created_by': to_json_value(self.created_by),
            'creation_date': to_json_value(self.creation_date),
            'last_update_date': to_json_value(self.last_update_date),
            'deletion_date': to_json_value(self.deletion_date),
        }

    def serialize_summary(self) -> dict:
        return {'id_material': self.id_material}
