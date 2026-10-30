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


class Theme(Base):
    __tablename__ = 'theme'

    id_theme: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)
    tenant_id: Mapped[int] = mapped_column(Integer, nullable=False)
    primary_color: Mapped[object] = mapped_column(String(10), nullable=False)
    secondary_color: Mapped[object] = mapped_column(String(10), nullable=False)
    background_color: Mapped[object] = mapped_column(String(10), nullable=False)
    text_color: Mapped[object] = mapped_column(String(10), nullable=False)
    highlight_color: Mapped[object] = mapped_column(String(10), nullable=False)
    success_color: Mapped[object] = mapped_column(String(10), nullable=False)
    error_color: Mapped[object] = mapped_column(String(10), nullable=False)

    def serialize(self) -> dict:
        return {
            'id_theme': to_json_value(self.id_theme),
            'created_by': to_json_value(self.created_by),
            'creation_date': a_iso_utc(self.creation_date),
            'last_update_date': a_iso_utc(self.last_update_date),
            'deletion_date': a_iso_utc(self.deletion_date),
            'tenant_id': to_json_value(self.tenant_id),
            'primary_color': to_json_value(self.primary_color),
            'secondary_color': to_json_value(self.secondary_color),
            'background_color': to_json_value(self.background_color),
            'text_color': to_json_value(self.text_color),
            'highlight_color': to_json_value(self.highlight_color),
            'success_color': to_json_value(self.success_color),
            'error_color': to_json_value(self.error_color),
        }

    def serialize_summary(self) -> dict:
        return {'id_theme': self.id_theme}
