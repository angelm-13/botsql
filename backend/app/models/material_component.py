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


class MaterialComponent(Base):
    __tablename__ = 'material_component'

    id_material_component: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    id_material: Mapped[int] = mapped_column(Integer, ForeignKey('material.id_material'), nullable=False)
    id_component: Mapped[int] = mapped_column(Integer, ForeignKey('material.id_material'), nullable=False)
    relation: Mapped[float] = mapped_column(Numeric(10,2), nullable=True)
    id_unit: Mapped[int] = mapped_column(Integer, ForeignKey('unit.id_unit'), nullable=False)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {
            'id_material_component': to_json_value(self.id_material_component),
            'id_material': to_json_value(self.id_material),
            'id_component': to_json_value(self.id_component),
            'relation': to_json_value(self.relation),
            'id_unit': to_json_value(self.id_unit),
            'created_by': to_json_value(self.created_by),
            'creation_date': a_iso_utc(self.creation_date),
            'last_update_date': a_iso_utc(self.last_update_date),
            'deletion_date': a_iso_utc(self.deletion_date),
        }

    def serialize_summary(self) -> dict:
        return {'id_material_component': self.id_material_component}
