from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import BigInteger, Integer, JSON, Date, DateTime, Numeric, ForeignKey, Index, UniqueConstraint, func
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


class KpiSnapshot(Base):
    """Cache diaria de un KPI, ya resuelto por dimension y periodo.

    No se declara como entidad del modulo "kpis" en
    `app/modules/registry.py`: esa lista es para lo que un usuario lista o
    edita por CRUD generico con `require_entity_permission`, y esta tabla no
    se toca asi -- la llena unicamente `app.jobs.tasks_kpis.
    recalculate_kpi_snapshots` (upsert) y se lee (en un endpoint propio, no
    generico) a traves del permiso ya existente sobre el KPI en
    `nm_permission_kpi`. Es el mismo criterio que separa `almacen=` de
    `entidades` en `Modulo`: una tabla derivada no reclama su propia fila de
    permisos.
    """

    __tablename__ = 'kpi_snapshot'
    __table_args__ = (
        UniqueConstraint('id_kpi_definition', 'dimension_key', 'periodo', name='uq_kpi_snapshot_dia'),
        Index('idx_kpi_snapshot_lookup', 'id_kpi_definition', 'periodo'),
    )

    id_kpi_snapshot: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, nullable=False)
    id_kpi_definition: Mapped[int] = mapped_column(Integer, ForeignKey('kpi_definition.id_kpi_definition'), nullable=False)
    # Para filtrar por contenido (`... WHERE dimension_key @> '{...}'`), hace
    # falta `sqlalchemy.cast(KpiSnapshot.dimension_key, JSONB).contains(...)`:
    # `.contains()` directo sobre esta columna usa el comparador del tipo
    # generico `JSON` (compila a `LIKE`, no a `@>`) porque `with_variant` solo
    # cambia el tipo en DDL/bind, no el comparador de Python. Visto al escribir
    # la prueba de la tarea de recalculo.
    dimension_key: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    periodo: Mapped[object] = mapped_column(Date, nullable=False)
    valor: Mapped[float] = mapped_column(Numeric, nullable=False)
    # Solo lo escriben los KPIs con `agregacion="promedio_ponderado"` (ver
    # AGREGACIONES en app/kpis/registry.py): cuantos casos hay detras de
    # `valor`. NULL para "suma"/"ultimo".
    peso: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    computed_at: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())

    def serialize(self) -> dict:
        return {
            'id_kpi_snapshot': to_json_value(self.id_kpi_snapshot),
            'id_kpi_definition': to_json_value(self.id_kpi_definition),
            'dimension_key': to_json_value(self.dimension_key),
            'periodo': to_json_value(self.periodo),
            'valor': to_json_value(self.valor),
            'peso': to_json_value(self.peso),
            'computed_at': to_json_value(self.computed_at),
        }

    def serialize_summary(self) -> dict:
        return {'id_kpi_snapshot': self.id_kpi_snapshot}
