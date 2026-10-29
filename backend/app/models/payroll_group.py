from __future__ import annotations
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Integer, String, func
from app.models.base import Base
from app.models.work_schedule import _auditoria, to_json_value

# Grupos de pago (migracion 20261028100000_grupos_de_pago.sql). Las reglas que
# los usan -que tarifa del ISR, que empleados entran a un periodo, que fechas
# siguen- viven en services/payroll_group_service.py.

SEMANAL, CATORCENAL, QUINCENAL, MENSUAL = "weekly", "biweekly", "semimonthly", "monthly"
PERIODICIDADES = (SEMANAL, CATORCENAL, QUINCENAL, MENSUAL)


class PayrollGroup(Base):
    """Un grupo de empleados que cobra con la misma periodicidad (Obreros: semanal).

    El grupo marcado `is_default` (uno solo) recibe a quien no tiene grupo asignado.
    """

    __tablename__ = 'payroll_group'
    __table_args__ = (
        CheckConstraint("pay_frequency IN ('weekly', 'biweekly', 'semimonthly', 'monthly')",
                        name='ck_payroll_group_frequency'),
    )

    id_payroll_group: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    group_name: Mapped[str] = mapped_column(String(120), nullable=False)
    pay_frequency: Mapped[str] = mapped_column(String(20), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default='false')
    created_by: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default='1')
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {'id_payroll_group': self.id_payroll_group, 'group_name': self.group_name,
                'pay_frequency': self.pay_frequency, 'is_default': bool(self.is_default), **_auditoria(self)}

    def serialize_summary(self) -> dict:
        return {'id_payroll_group': self.id_payroll_group}


class EmployeePayrollGroup(Base):
    """A que grupo de pago pertenece un empleado y desde/hasta cuando (valid_to nulo = sin fin)."""

    __tablename__ = 'employee_payroll_group'
    __table_args__ = (CheckConstraint('valid_to IS NULL OR valid_to >= valid_from',
                                      name='ck_employee_payroll_group_dates'),)

    id_employee_payroll_group: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True,
                                                           nullable=False)
    id_user: Mapped[int] = mapped_column(Integer, ForeignKey('user.id_user'), nullable=False)
    id_payroll_group: Mapped[int] = mapped_column(Integer, ForeignKey('payroll_group.id_payroll_group'), nullable=False)
    valid_from: Mapped[object] = mapped_column(Date, nullable=False)
    valid_to: Mapped[object] = mapped_column(Date, nullable=True)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default='1')
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {'id_employee_payroll_group': self.id_employee_payroll_group, 'id_user': self.id_user,
                'id_payroll_group': self.id_payroll_group, 'valid_from': to_json_value(self.valid_from),
                'valid_to': to_json_value(self.valid_to), **_auditoria(self)}

    def serialize_summary(self) -> dict:
        return {'id_employee_payroll_group': self.id_employee_payroll_group}
