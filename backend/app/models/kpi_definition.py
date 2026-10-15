from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, JSON, DateTime, func, text
from sqlalchemy.dialects.postgresql import JSONB
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


class KpiDefinition(Base):
    __tablename__ = 'kpi_definition'

    id_kpi_definition: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    clave: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    etiqueta: Mapped[str] = mapped_column(String(150), nullable=False)
    modulo: Mapped[str] = mapped_column(String(40), nullable=False)
    dimensiones: Mapped[list] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=list, server_default='[]')
    unidad: Mapped[str] = mapped_column(String(20), nullable=False, default='numero', server_default='numero')
    created_by: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default=text("1"))
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {
            'id_kpi_definition': to_json_value(self.id_kpi_definition),
            'clave': to_json_value(self.clave),
            'etiqueta': to_json_value(self.etiqueta),
            'modulo': to_json_value(self.modulo),
            'dimensiones': to_json_value(self.dimensiones),
            'unidad': to_json_value(self.unidad),
            'created_by': to_json_value(self.created_by),
            'creation_date': a_iso_utc(self.creation_date),
            'last_update_date': a_iso_utc(self.last_update_date),
            'deletion_date': a_iso_utc(self.deletion_date),
        }

    def serialize_summary(self) -> dict:
        return {'id_kpi_definition': self.id_kpi_definition}
