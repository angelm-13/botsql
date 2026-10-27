from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Date, Integer, String, DateTime, Numeric, UniqueConstraint, func
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


class PayrollParameter(Base):
    """Un valor oficial de nomina con su vigencia y su fuente.

    Claves que usa el calculo (payroll_calculation_service.py): uma_daily,
    uma_monthly, minimum_wage_daily, subsidy_pct, subsidy_income_limit,
    imss_em_surplus_pct, imss_em_cash_pct, imss_em_pensioners_pct, imss_iv_pct,
    imss_cv_pct, imss_surplus_umas, sbc_cap_umas, aguinaldo_days,
    vacation_premium_pct. `valid_to` nulo = sin fecha de fin.
    """

    __tablename__ = 'payroll_parameter'
    __table_args__ = (
        UniqueConstraint('parameter_key', 'valid_from', name='uq_payroll_parameter'),
    )

    id_payroll_parameter: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    parameter_key: Mapped[str] = mapped_column(String(40), nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    valid_from: Mapped[object] = mapped_column(Date, nullable=False)
    valid_to: Mapped[object] = mapped_column(Date, nullable=True)
    source: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default='1')
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {
            'id_payroll_parameter': to_json_value(self.id_payroll_parameter),
            'parameter_key': to_json_value(self.parameter_key),
            'value': to_json_value(self.value),
            'valid_from': to_json_value(self.valid_from),
            'valid_to': to_json_value(self.valid_to),
            'source': to_json_value(self.source),
            'created_by': to_json_value(self.created_by),
            'creation_date': a_iso_utc(self.creation_date),
            'last_update_date': a_iso_utc(self.last_update_date),
            'deletion_date': a_iso_utc(self.deletion_date),
        }

    def serialize_summary(self) -> dict:
        return {'id_payroll_parameter': self.id_payroll_parameter}
