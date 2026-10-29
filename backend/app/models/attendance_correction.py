from __future__ import annotations
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, func
from app.models.base import Base
from app.models.work_schedule import _auditoria, to_json_value

# Historial de correcciones de checadas (migracion 20261028120000). La regla
# -quien corrige, el limite por mes, la excepcion de RH- vive en
# services/attendance_correction_service.py.


class AttendanceCorrection(Base):
    """Una hora de checada corregida (o agregada) y por que.

    La correccion cambia la checada misma (`attendance_record.check_time`), asi
    el calculo usa una sola hora; aqui queda lo que decia antes, quien la
    cambio, cuando y el motivo.
    """

    __tablename__ = 'attendance_correction'

    id_attendance_correction: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    id_attendance_record: Mapped[int] = mapped_column(Integer, ForeignKey('attendance_record.id_attendance_record'),
                                                      nullable=False)
    id_user: Mapped[int] = mapped_column(Integer, ForeignKey('user.id_user'), nullable=False)
    # Dia de la checada: con el se cuenta el limite del mes.
    check_date: Mapped[object] = mapped_column(Date, nullable=False)
    previous_time: Mapped[object] = mapped_column(DateTime, nullable=True)   # nula = checada agregada
    new_time: Mapped[object] = mapped_column(DateTime, nullable=False)
    reason: Mapped[str] = mapped_column(String(300), nullable=False)
    # Hecha por RH cuando el empleado ya habia usado sus correcciones del mes.
    is_exception: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default='false')
    created_by: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default='1')
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {'id_attendance_correction': self.id_attendance_correction,
                'id_attendance_record': self.id_attendance_record, 'id_user': self.id_user,
                'check_date': to_json_value(self.check_date), 'previous_time': to_json_value(self.previous_time),
                'new_time': to_json_value(self.new_time), 'reason': self.reason,
                'is_exception': bool(self.is_exception), **_auditoria(self)}

    def serialize_summary(self) -> dict:
        return {'id_attendance_correction': self.id_attendance_correction}
