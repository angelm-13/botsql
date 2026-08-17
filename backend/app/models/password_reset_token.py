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


class PasswordResetToken(Base):
    __tablename__ = 'password_reset_token'

    id_password_reset_token: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    id_user: Mapped[int] = mapped_column(Integer, ForeignKey('user.id_user'), nullable=False)
    token_hash: Mapped[object] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[object] = mapped_column(DateTime, nullable=False)
    used_at: Mapped[object] = mapped_column(DateTime, nullable=True)
    requested_ip: Mapped[object] = mapped_column(String(45), nullable=True)
    created_at: Mapped[object] = mapped_column(DateTime, nullable=False)

    def serialize(self) -> dict:
        return {
            'id_password_reset_token': to_json_value(self.id_password_reset_token),
            'id_user': to_json_value(self.id_user),
            'token_hash': to_json_value(self.token_hash),
            'expires_at': to_json_value(self.expires_at),
            'used_at': to_json_value(self.used_at),
            'requested_ip': to_json_value(self.requested_ip),
            'created_at': to_json_value(self.created_at),
        }

    def serialize_summary(self) -> dict:
        return {'id_password_reset_token': self.id_password_reset_token}
