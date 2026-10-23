from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, DateTime, Text, ForeignKey, func
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
    # El destinatario. Nunca se lista "de todos" -- una notificacion es del
    # usuario que la recibe, no un dato de negocio compartido.
    id_user: Mapped[int] = mapped_column(Integer, ForeignKey('user.id_user'), nullable=False)
    id_proyect: Mapped[object] = mapped_column(Integer, ForeignKey('proyect.id_proyect'), nullable=True)
    id_proyect_event: Mapped[object] = mapped_column(Integer, ForeignKey('proyect_event.id_proyect_event'), nullable=True)
    notification_type: Mapped[object] = mapped_column(String(40), nullable=False)
    title: Mapped[object] = mapped_column(String(160), nullable=False)
    content: Mapped[object] = mapped_column(Text, nullable=True)
    read_at: Mapped[object] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())

    def serialize(self) -> dict:
        return {
            'id_notification': to_json_value(self.id_notification),
            'id_user': to_json_value(self.id_user),
            'id_proyect': to_json_value(self.id_proyect),
            'id_proyect_event': to_json_value(self.id_proyect_event),
            'notification_type': to_json_value(self.notification_type),
            'title': to_json_value(self.title),
            'content': to_json_value(self.content),
            'read_at': to_json_value(self.read_at),
            'created_by': to_json_value(self.created_by),
            'creation_date': to_json_value(self.creation_date),
        }

    def serialize_summary(self) -> dict:
        return {'id_notification': self.id_notification}
