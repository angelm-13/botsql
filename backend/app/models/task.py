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


class Task(Base):
    __tablename__ = 'task'

    id_task: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    task_code: Mapped[object] = mapped_column(String(11), nullable=True)
    start_date: Mapped[object] = mapped_column(DateTime, nullable=True)
    duration: Mapped[float] = mapped_column(Numeric(10,2), nullable=True)
    type: Mapped[object] = mapped_column(Enum('personal', 'business', name='task_type_enum', native_enum=False, validate_strings=True, create_constraint=True), nullable=True)
    owner: Mapped[int] = mapped_column(Integer, ForeignKey('user.id_user'), nullable=False)
    dependency: Mapped[int] = mapped_column(Integer, nullable=False)
    validation: Mapped[int] = mapped_column(Integer, nullable=False)
    task_description: Mapped[object] = mapped_column(String(200), nullable=False)
    estimated_effort: Mapped[object] = mapped_column(String(50), nullable=True)
    task_status: Mapped[object] = mapped_column(String(20), nullable=True)
    fase: Mapped[object] = mapped_column(String(100), nullable=True)
    priority: Mapped[object] = mapped_column(String(50), nullable=True)
    title: Mapped[object] = mapped_column(String(50), nullable=True)
    id_proyect: Mapped[int] = mapped_column(Integer, ForeignKey('proyect.id_proyect'), nullable=False)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {
            'id_task': to_json_value(self.id_task),
            'task_code': to_json_value(self.task_code),
            'start_date': to_json_value(self.start_date),
            'duration': to_json_value(self.duration),
            'type': to_json_value(self.type),
            'owner': to_json_value(self.owner),
            'dependency': to_json_value(self.dependency),
            'validation': to_json_value(self.validation),
            'task_description': to_json_value(self.task_description),
            'estimated_effort': to_json_value(self.estimated_effort),
            'task_status': to_json_value(self.task_status),
            'fase': to_json_value(self.fase),
            'priority': to_json_value(self.priority),
            'title': to_json_value(self.title),
            'id_proyect': to_json_value(self.id_proyect),
            'created_by': to_json_value(self.created_by),
            'creation_date': a_iso_utc(self.creation_date),
            'last_update_date': a_iso_utc(self.last_update_date),
            'deletion_date': a_iso_utc(self.deletion_date),
        }

    def serialize_summary(self) -> dict:
        return {'id_task': self.id_task}
