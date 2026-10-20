from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, BigInteger, SmallInteger, Boolean, Date, DateTime, Float, Numeric, ForeignKey, Text, JSON, Enum, LargeBinary, UniqueConstraint, CheckConstraint, func
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


class PayrollPeriod(Base):
    __tablename__ = 'payroll_period'
    # Mismo CHECK que la migracion 20261016120000_cierre_de_periodo_de_nomina.sql.
    __table_args__ = (
        CheckConstraint("period_state IN ('open', 'calculated', 'closed')", name='ck_payroll_period_state'),
    )

    id_payroll_period: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    period_start: Mapped[object] = mapped_column(Date, nullable=True)
    period_end: Mapped[object] = mapped_column(Date, nullable=True)
    payment_date: Mapped[object] = mapped_column(Date, nullable=True)
    id_status: Mapped[int] = mapped_column(Integer, ForeignKey('status.id_status'), nullable=False)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)
    # Abierto -> Calculado -> Cerrado (ver payroll_calculation_service.py). Solo
    # lo cambian calcular, cerrar y reabrir; la captura generica no lo escribe.
    period_state: Mapped[str] = mapped_column(String(20), nullable=False, default='open', server_default='open')
    closed_at: Mapped[object] = mapped_column(DateTime, nullable=True)
    closed_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reopened_at: Mapped[object] = mapped_column(DateTime, nullable=True)
    reopened_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Si esta marcada, el calculo paga el aguinaldo en este periodo
    # (migracion 20261020110000_aguinaldo_y_prima_vacacional.sql).
    includes_aguinaldo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default='false')

    def serialize(self) -> dict:
        return {
            'id_payroll_period': to_json_value(self.id_payroll_period),
            'period_start': to_json_value(self.period_start),
            'period_end': to_json_value(self.period_end),
            'payment_date': to_json_value(self.payment_date),
            'id_status': to_json_value(self.id_status),
            'created_by': to_json_value(self.created_by),
            'creation_date': a_iso_utc(self.creation_date),
            'last_update_date': a_iso_utc(self.last_update_date),
            'deletion_date': a_iso_utc(self.deletion_date),
            'period_state': to_json_value(self.period_state),
            'closed_at': a_iso_utc(self.closed_at),
            'closed_by': to_json_value(self.closed_by),
            'reopened_at': a_iso_utc(self.reopened_at),
            'reopened_by': to_json_value(self.reopened_by),
            'includes_aguinaldo': bool(self.includes_aguinaldo),
        }

    def serialize_summary(self) -> dict:
        return {'id_payroll_period': self.id_payroll_period}
