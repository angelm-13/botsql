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


class Notification(Base):
    __tablename__ = 'notification'

    id_notification: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    id_user_recipient: Mapped[int] = mapped_column(Integer, ForeignKey('user.id_user'), nullable=False, index=True)
    id_user_sender: Mapped[int | None] = mapped_column(Integer, ForeignKey('user.id_user'), nullable=True)
    id_proyect: Mapped[int | None] = mapped_column(Integer, ForeignKey('proyect.id_proyect'), nullable=True, index=True)
    notification_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default='custom',
        server_default='custom')
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default='false', index=True)
    read_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default={}, server_default='{}')
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey('user.id_user'), nullable=False)
    creation_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {
            'id_notification': to_json_value(self.id_notification),
            'id_user_recipient': to_json_value(self.id_user_recipient),
            'id_user_sender': to_json_value(self.id_user_sender),
            'id_proyect': to_json_value(self.id_proyect),
            'notification_type': to_json_value(self.notification_type),
            'title': to_json_value(self.title),
            'message': to_json_value(self.message),
            'is_read': to_json_value(self.is_read),
            'read_date': to_json_value(self.read_date),
            'metadata': to_json_value(self.metadata),
            'created_by': to_json_value(self.created_by),
            'creation_date': to_json_value(self.creation_date),
            'last_update_date': to_json_value(self.last_update_date),
            'deletion_date': to_json_value(self.deletion_date),
        }

    def serialize_summary(self) -> dict:
        return {
            'id_notification': self.id_notification,
            'title': self.title,
            'is_read': self.is_read,
            'creation_date': self.creation_date.isoformat() if self.creation_date else None,
        }
