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


class PayrollConcept(Base):
    __tablename__ = 'payroll_concept'

    id_payroll_concept: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    payroll_code: Mapped[object] = mapped_column(String(20), nullable=True)
    payroll_concept_description: Mapped[object] = mapped_column(String(150), nullable=False)
    type: Mapped[object] = mapped_column(Enum('earning', 'deduction', 'employer_contribution', name='payroll_concept_type_enum', native_enum=False, validate_strings=True, create_constraint=True), nullable=True)
    is_taxable: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_imss: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {
            'id_payroll_concept': to_json_value(self.id_payroll_concept),
            'payroll_code': to_json_value(self.payroll_code),
            'payroll_concept_description': to_json_value(self.payroll_concept_description),
            'type': to_json_value(self.type),
            'is_taxable': to_json_value(self.is_taxable),
            'is_imss': to_json_value(self.is_imss),
            'created_by': to_json_value(self.created_by),
            'creation_date': a_iso_utc(self.creation_date),
            'last_update_date': a_iso_utc(self.last_update_date),
            'deletion_date': a_iso_utc(self.deletion_date),
        }

    def serialize_summary(self) -> dict:
        return {'id_payroll_concept': self.id_payroll_concept}
