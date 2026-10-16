from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, String, DateTime, Numeric, UniqueConstraint, func
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


class PayrollIsrBracket(Base):
    """Un tramo de la tarifa del ISR para retenciones por salarios (art. 96 LISR).

    `period_days`: de que tabla es (1 diaria, 7, 10, 15, 30 mensual). Las cifras
    vienen del Anexo 8 de la RMF y se capturan cada año; ver la migracion
    20261016130000_tablas_isr_y_parametros_de_nomina.sql.
    """

    __tablename__ = 'payroll_isr_bracket'
    __table_args__ = (
        UniqueConstraint('period_days', 'valid_year', 'lower_limit', name='uq_payroll_isr_bracket'),
    )

    id_payroll_isr_bracket: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    period_days: Mapped[int] = mapped_column(Integer, nullable=False)
    valid_year: Mapped[int] = mapped_column(Integer, nullable=False)
    lower_limit: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    upper_limit: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    fixed_fee: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    rate_pct: Mapped[Decimal] = mapped_column(Numeric(6, 3), nullable=False)
    source: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default='1')
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {
            'id_payroll_isr_bracket': to_json_value(self.id_payroll_isr_bracket),
            'period_days': to_json_value(self.period_days),
            'valid_year': to_json_value(self.valid_year),
            'lower_limit': to_json_value(self.lower_limit),
            'upper_limit': to_json_value(self.upper_limit),
            'fixed_fee': to_json_value(self.fixed_fee),
            'rate_pct': to_json_value(self.rate_pct),
            'source': to_json_value(self.source),
            'created_by': to_json_value(self.created_by),
            'creation_date': a_iso_utc(self.creation_date),
            'last_update_date': a_iso_utc(self.last_update_date),
            'deletion_date': a_iso_utc(self.deletion_date),
        }

    def serialize_summary(self) -> dict:
        return {'id_payroll_isr_bracket': self.id_payroll_isr_bracket}
