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


class Movement(Base):
    __tablename__ = 'movement'

    id_movement: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    id_fiscal_account: Mapped[int] = mapped_column(Integer, ForeignKey('fiscal_account.id_fiscal_account'), nullable=False)
    date: Mapped[object] = mapped_column(DateTime, nullable=True)
    type: Mapped[object] = mapped_column(Enum('income', 'expense', name='movement_type_enum', native_enum=False, validate_strings=True, create_constraint=True), nullable=True)
    amount: Mapped[float] = mapped_column(Numeric(10,2), nullable=True)
    currency: Mapped[object] = mapped_column(Enum('usd', 'mxn', 'eur', name='movement_currency_enum', native_enum=False, validate_strings=True, create_constraint=True), nullable=True)
    type_exchange_rate: Mapped[float] = mapped_column(Numeric(10,2), nullable=True)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {
            'id_movement': to_json_value(self.id_movement),
            'id_fiscal_account': to_json_value(self.id_fiscal_account),
            'date': to_json_value(self.date),
            'type': to_json_value(self.type),
            'amount': to_json_value(self.amount),
            'currency': to_json_value(self.currency),
            'type_exchange_rate': to_json_value(self.type_exchange_rate),
            'created_by': to_json_value(self.created_by),
            'creation_date': a_iso_utc(self.creation_date),
            'last_update_date': a_iso_utc(self.last_update_date),
            'deletion_date': a_iso_utc(self.deletion_date),
        }

    def serialize_summary(self) -> dict:
        return {'id_movement': self.id_movement}
