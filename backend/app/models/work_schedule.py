from __future__ import annotations
from datetime import date, datetime, time
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import (CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, String, Time, UniqueConstraint,
                        func, text)
from app.models.base import Base
from app.utils.tiempo import a_iso_utc

# Horarios de trabajo, su asignacion y los festivos (migracion
# 20261020100000_horarios_y_dias_festivos.sql). Las reglas que los usan
# -retardos, faltas, dias pagados- viven en services/attendance_rules.py.


def to_json_value(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, time):
        return value.strftime("%H:%M")
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _auditoria(fila) -> dict:
    return {
        'created_by': fila.created_by,
        'creation_date': a_iso_utc(fila.creation_date),
        'last_update_date': a_iso_utc(fila.last_update_date),
        'deletion_date': a_iso_utc(fila.deletion_date),
    }


class WorkSchedule(Base):
    """Un horario con nombre y minutos de tolerancia para el retardo."""

    __tablename__ = 'work_schedule'
    __table_args__ = (CheckConstraint('tolerance_minutes BETWEEN 0 AND 240', name='ck_work_schedule_tolerance'),)

    id_work_schedule: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    schedule_name: Mapped[str] = mapped_column(String(120), nullable=False)
    tolerance_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=10, server_default='10')
    created_by: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default='1')
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {'id_work_schedule': self.id_work_schedule, 'schedule_name': self.schedule_name,
                'tolerance_minutes': self.tolerance_minutes, **_auditoria(self)}

    def serialize_summary(self) -> dict:
        return {'id_work_schedule': self.id_work_schedule}


class WorkScheduleDay(Base):
    """Un dia laboral de un horario (weekday 0 lunes ... 6 domingo)."""

    __tablename__ = 'work_schedule_day'
    __table_args__ = (
        CheckConstraint('weekday BETWEEN 0 AND 6', name='ck_work_schedule_day_weekday'),
        CheckConstraint('end_time > start_time', name='ck_work_schedule_day_hours'),
        Index('uq_work_schedule_day_vivo', 'id_work_schedule', 'weekday', unique=True,
              postgresql_where=text('deletion_date IS NULL'), sqlite_where=text('deletion_date IS NULL')),
    )

    id_work_schedule_day: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    id_work_schedule: Mapped[int] = mapped_column(Integer, ForeignKey('work_schedule.id_work_schedule'), nullable=False)
    weekday: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[object] = mapped_column(Time, nullable=False)
    end_time: Mapped[object] = mapped_column(Time, nullable=False)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default='1')
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {'id_work_schedule_day': self.id_work_schedule_day, 'id_work_schedule': self.id_work_schedule,
                'weekday': self.weekday, 'start_time': to_json_value(self.start_time),
                'end_time': to_json_value(self.end_time), **_auditoria(self)}

    def serialize_summary(self) -> dict:
        return {'id_work_schedule_day': self.id_work_schedule_day}


class EmployeeSchedule(Base):
    """Que horario tiene un empleado y desde/hasta cuando (valid_to nulo = sin fin)."""

    __tablename__ = 'employee_schedule'
    __table_args__ = (CheckConstraint('valid_to IS NULL OR valid_to >= valid_from', name='ck_employee_schedule_dates'),)

    id_employee_schedule: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    id_user: Mapped[int] = mapped_column(Integer, ForeignKey('user.id_user'), nullable=False)
    id_work_schedule: Mapped[int] = mapped_column(Integer, ForeignKey('work_schedule.id_work_schedule'), nullable=False)
    valid_from: Mapped[object] = mapped_column(Date, nullable=False)
    valid_to: Mapped[object] = mapped_column(Date, nullable=True)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default='1')
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {'id_employee_schedule': self.id_employee_schedule, 'id_user': self.id_user,
                'id_work_schedule': self.id_work_schedule, 'valid_from': to_json_value(self.valid_from),
                'valid_to': to_json_value(self.valid_to), **_auditoria(self)}

    def serialize_summary(self) -> dict:
        return {'id_employee_schedule': self.id_employee_schedule}


class PayrollHoliday(Base):
    """Un dia de descanso obligatorio (LFT art. 74)."""

    __tablename__ = 'payroll_holiday'
    __table_args__ = (UniqueConstraint('holiday_date', name='uq_payroll_holiday_date'),)

    id_payroll_holiday: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    holiday_date: Mapped[object] = mapped_column(Date, nullable=False)
    description: Mapped[str] = mapped_column(String(150), nullable=False)
    source: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default='1')
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {'id_payroll_holiday': self.id_payroll_holiday, 'holiday_date': to_json_value(self.holiday_date),
                'description': self.description, 'source': self.source, **_auditoria(self)}

    def serialize_summary(self) -> dict:
        return {'id_payroll_holiday': self.id_payroll_holiday}
