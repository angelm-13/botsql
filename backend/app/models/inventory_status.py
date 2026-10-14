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


class InventoryStatus(Base):
    __tablename__ = 'inventory_status'

    id_inventory_status: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    inventory_status_code: Mapped[object] = mapped_column(String(50), nullable=False)
    inventory_status_description: Mapped[object] = mapped_column(String(120), nullable=False)
    color: Mapped[object] = mapped_column(String(20), nullable=False)
    entity_scope: Mapped[object] = mapped_column(String(80), nullable=False)
    flow_scope: Mapped[object] = mapped_column(String(80), nullable=False)
    id_department: Mapped[int] = mapped_column(Integer, ForeignKey('department.id_department'), nullable=False)
    id_subdepartment: Mapped[int] = mapped_column(Integer, ForeignKey('subdepartment.id_subdepartment'), nullable=True)
    id_minimum_level: Mapped[int] = mapped_column(Integer, ForeignKey('level.id_level'), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_terminal: Mapped[bool] = mapped_column(Boolean, nullable=False)
    visible_to_other_departments: Mapped[bool] = mapped_column(Boolean, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {
            'id_inventory_status': to_json_value(self.id_inventory_status),
            'inventory_status_code': to_json_value(self.inventory_status_code),
            'inventory_status_description': to_json_value(self.inventory_status_description),
            'color': to_json_value(self.color),
            'entity_scope': to_json_value(self.entity_scope),
            'flow_scope': to_json_value(self.flow_scope),
            'id_department': to_json_value(self.id_department),
            'id_subdepartment': to_json_value(self.id_subdepartment),
            'id_minimum_level': to_json_value(self.id_minimum_level),
            'is_active': to_json_value(self.is_active),
            'is_terminal': to_json_value(self.is_terminal),
            'visible_to_other_departments': to_json_value(self.visible_to_other_departments),
            'sort_order': to_json_value(self.sort_order),
            'created_by': to_json_value(self.created_by),
            'creation_date': a_iso_utc(self.creation_date),
            'last_update_date': a_iso_utc(self.last_update_date),
            'deletion_date': a_iso_utc(self.deletion_date),
        }

    def serialize_summary(self) -> dict:
        return {'id_inventory_status': self.id_inventory_status}
