from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Boolean, Integer, DateTime, ForeignKey, UniqueConstraint, func, text
from app.models.base import Base


def to_json_value(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.hex()
    return value


class NmPermissionKpi(Base):
    __tablename__ = 'nm_permission_kpi'
    __table_args__ = (
        UniqueConstraint('id_permission', 'id_kpi_definition', name='uq_nm_permission_kpi'),
    )

    id_nm_permission_kpi: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    id_permission: Mapped[int] = mapped_column(Integer, nullable=False)
    id_kpi_definition: Mapped[int] = mapped_column(Integer, ForeignKey('kpi_definition.id_kpi_definition'), nullable=False)
    puede_ver: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    created_by: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default=text("1"))
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {
            'id_nm_permission_kpi': to_json_value(self.id_nm_permission_kpi),
            'id_permission': to_json_value(self.id_permission),
            'id_kpi_definition': to_json_value(self.id_kpi_definition),
            'puede_ver': to_json_value(self.puede_ver),
            'created_by': to_json_value(self.created_by),
            'creation_date': to_json_value(self.creation_date),
            'last_update_date': to_json_value(self.last_update_date),
            'deletion_date': to_json_value(self.deletion_date),
        }

    def serialize_summary(self) -> dict:
        return {'id_nm_permission_kpi': self.id_nm_permission_kpi}
