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


class SupervisorActivityLog(Base):
    __tablename__ = 'supervisor_activity_log'

    id_activity: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    id_proyect: Mapped[int] = mapped_column(Integer, ForeignKey('proyect.id_proyect'), nullable=False, index=True)
    id_supervisor: Mapped[int] = mapped_column(Integer, ForeignKey('user.id_user'), nullable=False, index=True)
    activity_date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default='pending', server_default='pending')
    hours_spent: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey('user.id_user'), nullable=False)
    creation_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {
            'id_activity': to_json_value(self.id_activity),
            'id_proyect': to_json_value(self.id_proyect),
            'id_supervisor': to_json_value(self.id_supervisor),
            'activity_date': to_json_value(self.activity_date),
            'description': to_json_value(self.description),
            'status': to_json_value(self.status),
            'hours_spent': to_json_value(self.hours_spent),
            'notes': to_json_value(self.notes),
            'created_by': to_json_value(self.created_by),
            'creation_date': a_iso_utc(self.creation_date),
            'last_update_date': a_iso_utc(self.last_update_date),
            'deletion_date': a_iso_utc(self.deletion_date),
        }

    def serialize_summary(self) -> dict:
        return {
            'id_activity': self.id_activity,
            'id_proyect': self.id_proyect,
            'activity_date': self.activity_date.isoformat() if self.activity_date else None,
            'description': self.description[:100],
            'status': self.status,
        }
