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


class TaskNote(Base):
    __tablename__ = 'task_note'

    id_task_note: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    date: Mapped[object] = mapped_column(DateTime, nullable=True)
    id_task: Mapped[int] = mapped_column(Integer, ForeignKey('task.id_task'), nullable=False)
    task_note_description: Mapped[object] = mapped_column(String(600), nullable=False)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {
            'id_task_note': to_json_value(self.id_task_note),
            'date': to_json_value(self.date),
            'id_task': to_json_value(self.id_task),
            'task_note_description': to_json_value(self.task_note_description),
            'created_by': to_json_value(self.created_by),
            'creation_date': a_iso_utc(self.creation_date),
            'last_update_date': a_iso_utc(self.last_update_date),
            'deletion_date': a_iso_utc(self.deletion_date),
        }

    def serialize_summary(self) -> dict:
        return {'id_task_note': self.id_task_note}
