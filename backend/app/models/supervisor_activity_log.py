from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, Date, DateTime, Text, ForeignKey, func
from app.models.base import Base


def to_json_value(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.hex()
    return value


class SupervisorActivityLog(Base):
    __tablename__ = 'supervisor_activity_log'

    id_supervisor_activity_log: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    # Quien captura la actividad. No necesariamente el rol de negocio
    # "Supervisor" -- cualquiera con el permiso puede llevar su bitacora --,
    # pero es a quien se le reclama si falta un dia.
    id_user: Mapped[int] = mapped_column(Integer, ForeignKey('user.id_user'), nullable=False)
    activity_date: Mapped[object] = mapped_column(Date, nullable=False)
    content: Mapped[object] = mapped_column(Text, nullable=False)
    id_proyect: Mapped[object] = mapped_column(Integer, ForeignKey('proyect.id_proyect'), nullable=True)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {
            'id_supervisor_activity_log': to_json_value(self.id_supervisor_activity_log),
            'id_user': to_json_value(self.id_user),
            'activity_date': to_json_value(self.activity_date),
            'content': to_json_value(self.content),
            'id_proyect': to_json_value(self.id_proyect),
            'created_by': to_json_value(self.created_by),
            'creation_date': to_json_value(self.creation_date),
            'last_update_date': to_json_value(self.last_update_date),
            'deletion_date': to_json_value(self.deletion_date),
        }

    def serialize_summary(self) -> dict:
        return {'id_supervisor_activity_log': self.id_supervisor_activity_log}
