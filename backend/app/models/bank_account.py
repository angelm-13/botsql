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


class BankAccount(Base):
    __tablename__ = 'bank_account'

    id_bank_account: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    id_bank: Mapped[int] = mapped_column(Integer, ForeignKey('bank.id_bank'), nullable=False)
    bank_account_description: Mapped[object] = mapped_column(String(200), nullable=False)
    branch: Mapped[object] = mapped_column(String(30), nullable=True)
    type: Mapped[object] = mapped_column(String(30), nullable=True)
    ordinary_interest: Mapped[float] = mapped_column(Numeric(10,2), nullable=True)
    moratorium_interest: Mapped[float] = mapped_column(Numeric(10,2), nullable=True)
    anuality: Mapped[float] = mapped_column(Numeric(10,2), nullable=True)
    reimbursement: Mapped[float] = mapped_column(Numeric(10,2), nullable=True)
    id_proyect: Mapped[int] = mapped_column(Integer, ForeignKey('proyect.id_proyect'), nullable=True)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {
            'id_bank_account': to_json_value(self.id_bank_account),
            'id_bank': to_json_value(self.id_bank),
            'bank_account_description': to_json_value(self.bank_account_description),
            'branch': to_json_value(self.branch),
            'type': to_json_value(self.type),
            'ordinary_interest': to_json_value(self.ordinary_interest),
            'moratorium_interest': to_json_value(self.moratorium_interest),
            'anuality': to_json_value(self.anuality),
            'reimbursement': to_json_value(self.reimbursement),
            'id_proyect': to_json_value(self.id_proyect),
            'created_by': to_json_value(self.created_by),
            'creation_date': to_json_value(self.creation_date),
            'last_update_date': to_json_value(self.last_update_date),
            'deletion_date': to_json_value(self.deletion_date),
        }

    def serialize_summary(self) -> dict:
        return {'id_bank_account': self.id_bank_account}
