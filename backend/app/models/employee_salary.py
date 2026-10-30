from __future__ import annotations
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Integer, Numeric, String, func
from app.models.base import Base
from app.models.work_schedule import _auditoria, to_json_value

# Forma de salario de cada empleado (migracion 20261030110000). Las reglas -como
# se paga cada forma, su diario equivalente, el precio de su hora extra- viven
# en services/salary_service.py.

POR_DIA, POR_HORA, FIJO = "daily", "hourly", "fixed"
FORMAS = (POR_DIA, POR_HORA, FIJO)
# Un sueldo fijo es por semana, catorcena, quincena o mes; en dias:
DIAS_DEL_FIJO = {"weekly": 7, "biweekly": 14, "semimonthly": 15, "monthly": 30}


class EmployeeSalary(Base):
    """Como gana un empleado desde/hasta cuando (valid_to nulo = sin fin): por dia
    ($500 al dia), por hora ($65 la hora) o fijo por periodo ($7,500 la quincena).
    Guarda el historial de aumentos."""

    __tablename__ = 'employee_salary'
    __table_args__ = (
        CheckConstraint("salary_type IN ('daily', 'hourly', 'fixed')", name='ck_employee_salary_type'),
        CheckConstraint("fixed_frequency IS NULL OR fixed_frequency IN ('weekly', 'biweekly', 'semimonthly', 'monthly')",
                        name='ck_employee_salary_frequency'),
        CheckConstraint('amount > 0', name='ck_employee_salary_amount'),
        CheckConstraint('valid_to IS NULL OR valid_to >= valid_from', name='ck_employee_salary_dates'),
    )

    id_employee_salary: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    id_user: Mapped[int] = mapped_column(Integer, ForeignKey('user.id_user'), nullable=False)
    salary_type: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[object] = mapped_column(Numeric(12, 2), nullable=False)
    fixed_frequency: Mapped[str | None] = mapped_column(String(20), nullable=True)
    valid_from: Mapped[object] = mapped_column(Date, nullable=False)
    valid_to: Mapped[object] = mapped_column(Date, nullable=True)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default='1')
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {'id_employee_salary': self.id_employee_salary, 'id_user': self.id_user,
                'salary_type': self.salary_type, 'amount': to_json_value(self.amount),
                'fixed_frequency': self.fixed_frequency, 'valid_from': to_json_value(self.valid_from),
                'valid_to': to_json_value(self.valid_to), **_auditoria(self)}

    def serialize_summary(self) -> dict:
        return {'id_employee_salary': self.id_employee_salary}
