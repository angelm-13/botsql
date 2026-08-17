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


class PayrollMovement(Base):
    __tablename__ = 'payroll_movement'

    id_payroll_movement: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    id_payroll_detail: Mapped[int] = mapped_column(Integer, ForeignKey('payroll_detail.id_payroll_detail'), nullable=False)
    id_payroll_concept: Mapped[int] = mapped_column(Integer, ForeignKey('payroll_concept.id_payroll_concept'), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12,2), nullable=True)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {
            'id_payroll_movement': to_json_value(self.id_payroll_movement),
            'id_payroll_detail': to_json_value(self.id_payroll_detail),
            'id_payroll_concept': to_json_value(self.id_payroll_concept),
            'amount': to_json_value(self.amount),
            'created_by': to_json_value(self.created_by),
            'creation_date': to_json_value(self.creation_date),
            'last_update_date': to_json_value(self.last_update_date),
            'deletion_date': to_json_value(self.deletion_date),
        }

    def serialize_summary(self) -> dict:
        return {'id_payroll_movement': self.id_payroll_movement}
