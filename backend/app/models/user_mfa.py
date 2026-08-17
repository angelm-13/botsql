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


class UserMfa(Base):
    __tablename__ = 'user_mfa'

    id_user_mfa: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    id_user: Mapped[int] = mapped_column(Integer, ForeignKey('user.id_user'), nullable=False)
    secret: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    secret_iv: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    failed_attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    locked_until: Mapped[object] = mapped_column(DateTime, nullable=True)
    last_used_at: Mapped[object] = mapped_column(DateTime, nullable=True)
    backup_codes: Mapped[object] = mapped_column(JSON, nullable=True)
    created_at: Mapped[object] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[object] = mapped_column(DateTime, nullable=False)

    def serialize(self) -> dict:
        return {
            'id_user_mfa': to_json_value(self.id_user_mfa),
            'id_user': to_json_value(self.id_user),
            'secret': to_json_value(self.secret),
            'secret_iv': to_json_value(self.secret_iv),
            'enabled': to_json_value(self.enabled),
            'failed_attempts': to_json_value(self.failed_attempts),
            'locked_until': to_json_value(self.locked_until),
            'last_used_at': to_json_value(self.last_used_at),
            'backup_codes': to_json_value(self.backup_codes),
            'created_at': to_json_value(self.created_at),
            'updated_at': to_json_value(self.updated_at),
        }

    def serialize_summary(self) -> dict:
        return {'id_user_mfa': self.id_user_mfa}
