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


class PayrollDetail(Base):
    __tablename__ = 'payroll_detail'

    id_payroll_detail: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    id_payroll_period: Mapped[int] = mapped_column(Integer, ForeignKey('payroll_period.id_payroll_period'), nullable=False)
    id_user: Mapped[int] = mapped_column(Integer, ForeignKey('user.id_user'), nullable=False)
    gross_salary: Mapped[float] = mapped_column(Numeric(12,2), nullable=True)
    total_earnings: Mapped[float] = mapped_column(Numeric(12,2), nullable=True)
    total_deductions: Mapped[float] = mapped_column(Numeric(12,2), nullable=True)
    net_pay: Mapped[float] = mapped_column(Numeric(12,2), nullable=True)
    # Dias con checada que uso el calculo de nomina; los muestra el recibo.
    days_worked: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {
            'id_payroll_detail': to_json_value(self.id_payroll_detail),
            'id_payroll_period': to_json_value(self.id_payroll_period),
            'id_user': to_json_value(self.id_user),
            'gross_salary': to_json_value(self.gross_salary),
            'total_earnings': to_json_value(self.total_earnings),
            'total_deductions': to_json_value(self.total_deductions),
            'net_pay': to_json_value(self.net_pay),
            'days_worked': to_json_value(self.days_worked),
            'created_by': to_json_value(self.created_by),
            'creation_date': a_iso_utc(self.creation_date),
            'last_update_date': a_iso_utc(self.last_update_date),
            'deletion_date': a_iso_utc(self.deletion_date),
        }

    def serialize_summary(self) -> dict:
        return {'id_payroll_detail': self.id_payroll_detail}
