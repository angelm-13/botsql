from __future__ import annotations
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Integer, String, func
from app.models.base import Base
from app.models.work_schedule import _auditoria, to_json_value

# Bajas de empleados (migracion 20261102120000). El calculo del finiquito o la
# liquidacion vive en services/termination_service.py; no se guarda: se calcula
# con los datos del dia (checadas, vacaciones, nomina ya pagada).

RENUNCIA, MUTUO_ACUERDO, DESPIDO_JUSTIFICADO, DESPIDO_INJUSTIFICADO = (
    "resignation", "mutual_agreement", "justified_dismissal", "unjustified_dismissal")
MOTIVOS = (RENUNCIA, MUTUO_ACUERDO, DESPIDO_JUSTIFICADO, DESPIDO_INJUSTIFICADO)


class EmployeeTermination(Base):
    """La baja de un empleado: fecha (ultimo dia trabajado), motivo y, en despido
    injustificado, si se pagan los 20 dias por año (LFT art. 50)."""

    __tablename__ = 'employee_termination'
    __table_args__ = (
        CheckConstraint("reason IN ('resignation', 'mutual_agreement', 'justified_dismissal', 'unjustified_dismissal')",
                        name='ck_employee_termination_reason'),
    )

    id_employee_termination: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    id_user: Mapped[int] = mapped_column(Integer, ForeignKey('user.id_user'), nullable=False)
    termination_date: Mapped[object] = mapped_column(Date, nullable=False)
    reason: Mapped[str] = mapped_column(String(30), nullable=False)
    pay_twenty_days: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default='false')
    notes: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default='1')
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {'id_employee_termination': self.id_employee_termination, 'id_user': self.id_user,
                'termination_date': to_json_value(self.termination_date), 'reason': self.reason,
                'pay_twenty_days': bool(self.pay_twenty_days), 'notes': self.notes, **_auditoria(self)}

    def serialize_summary(self) -> dict:
        return {'id_employee_termination': self.id_employee_termination}
