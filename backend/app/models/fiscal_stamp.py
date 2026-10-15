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


class FiscalStamp(Base):
    __tablename__ = 'fiscal_stamp'

    id_fiscal_stamp: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    concept: Mapped[object] = mapped_column(String(50), nullable=False)
    reviewed_by: Mapped[int] = mapped_column(Integer, nullable=False)
    authorized_by: Mapped[int] = mapped_column(Integer, nullable=False)
    auxiliar: Mapped[object] = mapped_column(String(50), nullable=True)
    num_policy: Mapped[object] = mapped_column(String(20), nullable=False)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {
            'id_fiscal_stamp': to_json_value(self.id_fiscal_stamp),
            'concept': to_json_value(self.concept),
            'reviewed_by': to_json_value(self.reviewed_by),
            'authorized_by': to_json_value(self.authorized_by),
            'auxiliar': to_json_value(self.auxiliar),
            'num_policy': to_json_value(self.num_policy),
            'created_by': to_json_value(self.created_by),
            'creation_date': a_iso_utc(self.creation_date),
            'last_update_date': a_iso_utc(self.last_update_date),
            'deletion_date': a_iso_utc(self.deletion_date),
        }

    def serialize_summary(self) -> dict:
        return {'id_fiscal_stamp': self.id_fiscal_stamp}
