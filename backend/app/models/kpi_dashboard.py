from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, DateTime, func
from app.models.base import Base


def to_json_value(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.hex()
    return value


class KpiDashboard(Base):
    __tablename__ = 'kpi_dashboard'

    id_kpi_dashboard: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    id_user: Mapped[int] = mapped_column(Integer, nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    orden: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {
            'id_kpi_dashboard': to_json_value(self.id_kpi_dashboard),
            'id_user': to_json_value(self.id_user),
            'nombre': to_json_value(self.nombre),
            'orden': to_json_value(self.orden),
            'created_by': to_json_value(self.created_by),
            'creation_date': to_json_value(self.creation_date),
            'last_update_date': to_json_value(self.last_update_date),
            'deletion_date': to_json_value(self.deletion_date),
        }

    def serialize_summary(self) -> dict:
        return {'id_kpi_dashboard': self.id_kpi_dashboard}
