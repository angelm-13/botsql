from __future__ import annotations
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Integer, String, func
from app.models.base import Base
from app.models.work_schedule import _auditoria, to_json_value
from app.utils.tiempo import a_iso_utc

# Ausencias justificadas: vacaciones, permisos e incapacidades (migracion
# 20261021100000_vacaciones_permisos_incapacidades.sql). Que dia es falta y cual
# se paga lo decide services/attendance_rules.py; el saldo de vacaciones y las
# validaciones, services/employee_leave_service.py.

TIPOS_DE_AUSENCIA = ('vacation', 'paid_leave', 'unpaid_leave', 'disability')
# Estado de la ausencia (migracion 20261022100000): solo lo aprobado cuenta;
# lo solicitado aparta dias del saldo de vacaciones.
SOLICITADA, APROBADA, RECHAZADA, CANCELADA = 'requested', 'approved', 'rejected', 'cancelled'
ESTADOS_DE_AUSENCIA = (SOLICITADA, APROBADA, RECHAZADA, CANCELADA)
ESTADOS_VIGENTES = (SOLICITADA, APROBADA)


class EmployeeLeave(Base):
    """Una ausencia justificada de un empleado, de `start_date` a `end_date`."""

    __tablename__ = 'employee_leave'
    __table_args__ = (
        CheckConstraint("leave_type IN ('vacation', 'paid_leave', 'unpaid_leave', 'disability')",
                        name='ck_employee_leave_type'),
        CheckConstraint('end_date >= start_date', name='ck_employee_leave_dates'),
        CheckConstraint("leave_status IN ('requested', 'approved', 'rejected', 'cancelled')",
                        name='ck_employee_leave_status'),
    )

    id_employee_leave: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    id_user: Mapped[int] = mapped_column(Integer, ForeignKey('user.id_user'), nullable=False)
    leave_type: Mapped[str] = mapped_column(String(20), nullable=False)
    start_date: Mapped[object] = mapped_column(Date, nullable=False)
    end_date: Mapped[object] = mapped_column(Date, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(300), nullable=True)
    leave_status: Mapped[str] = mapped_column(String(20), nullable=False, default=APROBADA, server_default=APROBADA)
    requested_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reviewed_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reviewed_at: Mapped[object] = mapped_column(DateTime, nullable=True)
    review_note: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default='1')
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {'id_employee_leave': self.id_employee_leave, 'id_user': self.id_user,
                'leave_type': self.leave_type, 'start_date': to_json_value(self.start_date),
                'end_date': to_json_value(self.end_date), 'notes': self.notes,
                'leave_status': self.leave_status, 'requested_by': self.requested_by,
                'reviewed_by': self.reviewed_by, 'reviewed_at': a_iso_utc(self.reviewed_at),
                'review_note': self.review_note, **_auditoria(self)}

    def serialize_summary(self) -> dict:
        return {'id_employee_leave': self.id_employee_leave}
