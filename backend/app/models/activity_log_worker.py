from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, DateTime, ForeignKey, UniqueConstraint, func
from app.models.base import Base


def to_json_value(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.hex()
    return value


class ActivityLogWorker(Base):
    """Quien de la plantilla del Jefe de taller trabajo en esta bitacora.

    Puente aparte de `supervisor_activity_log`: no todos los dias participa
    todo el equipo, y se necesita poder contar/filtrar por obrero despues.
    """
    __tablename__ = 'activity_log_worker'
    __table_args__ = (
        UniqueConstraint('id_activity', 'id_user', name='uq_activity_log_worker'),
    )

    id_activity_log_worker: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    id_activity: Mapped[int] = mapped_column(Integer, ForeignKey('supervisor_activity_log.id_activity'), nullable=False)
    id_user: Mapped[int] = mapped_column(Integer, ForeignKey('user.id_user'), nullable=False)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {
            'id_activity_log_worker': to_json_value(self.id_activity_log_worker),
            'id_activity': to_json_value(self.id_activity),
            'id_user': to_json_value(self.id_user),
            'created_by': to_json_value(self.created_by),
            'creation_date': to_json_value(self.creation_date),
            'deletion_date': to_json_value(self.deletion_date),
        }
