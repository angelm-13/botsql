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


class Ticket(Base):
    __tablename__ = 'ticket'

    id_ticket: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    ticket_description: Mapped[object] = mapped_column(String(200), nullable=False)
    ticket_status: Mapped[object] = mapped_column(String(20), nullable=True)
    note: Mapped[object] = mapped_column(String(300), nullable=True)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {
            'id_ticket': to_json_value(self.id_ticket),
            'ticket_description': to_json_value(self.ticket_description),
            'ticket_status': to_json_value(self.ticket_status),
            'note': to_json_value(self.note),
            'created_by': to_json_value(self.created_by),
            'creation_date': a_iso_utc(self.creation_date),
            'last_update_date': a_iso_utc(self.last_update_date),
            'deletion_date': a_iso_utc(self.deletion_date),
        }

    def serialize_summary(self) -> dict:
        return {'id_ticket': self.id_ticket}
