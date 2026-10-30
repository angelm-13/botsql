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


class FiscalRecord(Base):
    __tablename__ = 'fiscal_record'

    id_fiscal_record: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    fiscal_record_name: Mapped[object] = mapped_column(String(150), nullable=False)
    id_fiscal_account: Mapped[int] = mapped_column(Integer, ForeignKey('fiscal_account.id_fiscal_account'), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(10,2), nullable=False)
    type: Mapped[object] = mapped_column(String(30), nullable=True)
    id_fiscal_stamp: Mapped[int] = mapped_column(Integer, ForeignKey('fiscal_stamp.id_fiscal_stamp'), nullable=False)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {
            'id_fiscal_record': to_json_value(self.id_fiscal_record),
            'fiscal_record_name': to_json_value(self.fiscal_record_name),
            'id_fiscal_account': to_json_value(self.id_fiscal_account),
            'amount': to_json_value(self.amount),
            'type': to_json_value(self.type),
            'id_fiscal_stamp': to_json_value(self.id_fiscal_stamp),
            'created_by': to_json_value(self.created_by),
            'creation_date': a_iso_utc(self.creation_date),
            'last_update_date': a_iso_utc(self.last_update_date),
            'deletion_date': a_iso_utc(self.deletion_date),
        }

    def serialize_summary(self) -> dict:
        return {'id_fiscal_record': self.id_fiscal_record}
