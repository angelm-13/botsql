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


class PublicApiKey(Base):
    __tablename__ = 'public_api_key'

    id_public_api_key: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    label: Mapped[object] = mapped_column(String(120), nullable=False)
    key_hash: Mapped[object] = mapped_column(String(255), nullable=False)
    key_prefix: Mapped[object] = mapped_column(String(12), nullable=False)
    allowed_domains: Mapped[object] = mapped_column(Text, nullable=False)
    rate_limit_per_min: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    last_used_at: Mapped[object] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {
            'id_public_api_key': to_json_value(self.id_public_api_key),
            'label': to_json_value(self.label),
            'key_hash': to_json_value(self.key_hash),
            'key_prefix': to_json_value(self.key_prefix),
            'allowed_domains': to_json_value(self.allowed_domains),
            'rate_limit_per_min': to_json_value(self.rate_limit_per_min),
            'is_active': to_json_value(self.is_active),
            'last_used_at': to_json_value(self.last_used_at),
            'created_by': to_json_value(self.created_by),
            'creation_date': to_json_value(self.creation_date),
            'last_update_date': to_json_value(self.last_update_date),
            'deletion_date': to_json_value(self.deletion_date),
        }

    def serialize_summary(self) -> dict:
        return {'id_public_api_key': self.id_public_api_key}
