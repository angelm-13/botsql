from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, ForeignKey, UniqueConstraint, text
from app.models.base import Base


def to_json_value(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.hex()
    return value


class KpiDashboardWidgetKpi(Base):
    """Un KPI dentro de un widget: un widget puede mostrar varios a la vez.

    Puente entre `kpi_dashboard_widget` y `kpi_definition` -- ver la migracion
    `20260908210000_kpi_dashboard_widget_multi_kpi.sql`, que reemplazo la FK
    unica `kpi_dashboard_widget.id_kpi_definition` por esta tabla.
    """

    __tablename__ = 'kpi_dashboard_widget_kpi'
    __table_args__ = (
        UniqueConstraint('id_kpi_dashboard_widget', 'id_kpi_definition', name='uq_kpi_dashboard_widget_kpi'),
    )

    id_kpi_dashboard_widget_kpi: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    id_kpi_dashboard_widget: Mapped[int] = mapped_column(Integer, ForeignKey('kpi_dashboard_widget.id_kpi_dashboard_widget'), nullable=False)
    id_kpi_definition: Mapped[int] = mapped_column(Integer, ForeignKey('kpi_definition.id_kpi_definition'), nullable=False)
    orden: Mapped[int] = mapped_column(Integer, nullable=False, default=100, server_default=text("100"))

    def serialize(self) -> dict:
        return {
            'id_kpi_dashboard_widget_kpi': to_json_value(self.id_kpi_dashboard_widget_kpi),
            'id_kpi_dashboard_widget': to_json_value(self.id_kpi_dashboard_widget),
            'id_kpi_definition': to_json_value(self.id_kpi_definition),
            'orden': to_json_value(self.orden),
        }

    def serialize_summary(self) -> dict:
        return {'id_kpi_dashboard_widget_kpi': self.id_kpi_dashboard_widget_kpi}
