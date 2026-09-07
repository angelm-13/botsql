from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, JSON, DateTime, ForeignKey, func, text
from sqlalchemy.dialects.postgresql import JSONB
from app.models.base import Base


def to_json_value(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.hex()
    return value


class KpiDashboardWidget(Base):
    __tablename__ = 'kpi_dashboard_widget'

    id_kpi_dashboard_widget: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    id_kpi_dashboard: Mapped[int] = mapped_column(Integer, ForeignKey('kpi_dashboard.id_kpi_dashboard'), nullable=False)
    id_kpi_definition: Mapped[int] = mapped_column(Integer, ForeignKey('kpi_definition.id_kpi_definition'), nullable=False)
    tipo_grafica: Mapped[str] = mapped_column(String(30), nullable=False)
    parametros: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict, server_default='{}')
    posicion_orden: Mapped[int] = mapped_column(Integer, nullable=False, default=100, server_default=text("100"))
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {
            'id_kpi_dashboard_widget': to_json_value(self.id_kpi_dashboard_widget),
            'id_kpi_dashboard': to_json_value(self.id_kpi_dashboard),
            'id_kpi_definition': to_json_value(self.id_kpi_definition),
            'tipo_grafica': to_json_value(self.tipo_grafica),
            'parametros': to_json_value(self.parametros),
            'posicion_orden': to_json_value(self.posicion_orden),
            'creation_date': to_json_value(self.creation_date),
            'deletion_date': to_json_value(self.deletion_date),
        }

    def serialize_summary(self) -> dict:
        return {'id_kpi_dashboard_widget': self.id_kpi_dashboard_widget}
