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


class EventLog(Base):
    __tablename__ = 'event_log'

    id_event_log: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    table_name: Mapped[object] = mapped_column(String(50), nullable=False)
    field_name: Mapped[object] = mapped_column(String(50), nullable=False)
    action: Mapped[object] = mapped_column(Enum('create', 'update', 'delete', name='event_log_action_enum', native_enum=False, validate_strings=True, create_constraint=True), nullable=False)
    before_value: Mapped[object] = mapped_column(JSON, nullable=False)
    after_value: Mapped[object] = mapped_column(JSON, nullable=False)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {
            'id_event_log': to_json_value(self.id_event_log),
            'table_name': to_json_value(self.table_name),
            'field_name': to_json_value(self.field_name),
            'action': to_json_value(self.action),
            'before_value': to_json_value(self.before_value),
            'after_value': to_json_value(self.after_value),
            'created_by': to_json_value(self.created_by),
            'creation_date': to_json_value(self.creation_date),
            'last_update_date': to_json_value(self.last_update_date),
            'deletion_date': to_json_value(self.deletion_date),
        }

    def serialize_summary(self) -> dict:
        return {'id_event_log': self.id_event_log}
