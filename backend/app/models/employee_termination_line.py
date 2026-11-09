from __future__ import annotations
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String, func
from app.models.base import Base
from app.models.work_schedule import _auditoria

# Otros pagos y descuentos del finiquito (migracion 20261105130000), como en el Excel
# de la contadora: bonos o pagos pendientes que se suman, e Infonavit, Fonacot o
# deudas que se restan. Se editan desde la baja con su permiso (employee_termination),
# como las correcciones de checadas: sin entrada propia en el Gestor.

OTRO_PAGO, OTRO_DESCUENTO = "earning", "deduction"
TIPOS_DE_RENGLON = (OTRO_PAGO, OTRO_DESCUENTO)


class EmployeeTerminationLine(Base):
    __tablename__ = 'employee_termination_line'
    __table_args__ = (
        CheckConstraint("line_kind IN ('earning', 'deduction')", name='ck_employee_termination_line_kind'),
        CheckConstraint("amount > 0", name='ck_employee_termination_line_amount'),
    )

    id_employee_termination_line: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    id_employee_termination: Mapped[int] = mapped_column(
        Integer, ForeignKey('employee_termination.id_employee_termination'), nullable=False)
    line_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str] = mapped_column(String(120), nullable=False)
    amount: Mapped[object] = mapped_column(Numeric(12, 2), nullable=False)
    taxable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default='true')
    created_by: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default='1')
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {'id_employee_termination_line': self.id_employee_termination_line,
                'id_employee_termination': self.id_employee_termination, 'line_kind': self.line_kind,
                'description': self.description, 'amount': float(self.amount), 'taxable': bool(self.taxable),
                **_auditoria(self)}

    def serialize_summary(self) -> dict:
        return {'id_employee_termination_line': self.id_employee_termination_line}

