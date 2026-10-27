from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, DateTime, UniqueConstraint, func
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


class AttendanceRecord(Base):
    """Una checada de asistencia, tal como llego de su origen."""

    __tablename__ = 'attendance_record'
    __table_args__ = (
        UniqueConstraint('source', 'source_ref', name='uq_attendance_record_source_ref'),
        CheckConstraint("source IN ('kronos', 'whatsapp', 'manual')", name='ck_attendance_record_source'),
    )

    id_attendance_record: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    id_user: Mapped[int | None] = mapped_column(Integer, ForeignKey('user.id_user'), nullable=True)
    employee_no: Mapped[str] = mapped_column(String(32), nullable=False)
    employee_name: Mapped[str | None] = mapped_column(String(96), nullable=True)
    # Hora de pared del negocio, sin zona (ver app/utils/tiempo.py).
    check_time: Mapped[object] = mapped_column(DateTime, nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default='kronos', server_default='kronos')
    source_ref: Mapped[str] = mapped_column(String(64), nullable=False)
    door_no: Mapped[str | None] = mapped_column(String(16), nullable=True)
    verify_mode: Mapped[str | None] = mapped_column(String(40), nullable=True)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {
            'id_attendance_record': to_json_value(self.id_attendance_record),
            'id_user': to_json_value(self.id_user),
            'employee_no': to_json_value(self.employee_no),
            'employee_name': to_json_value(self.employee_name),
            'check_time': to_json_value(self.check_time),
            'source': to_json_value(self.source),
            'source_ref': to_json_value(self.source_ref),
            'door_no': to_json_value(self.door_no),
            'verify_mode': to_json_value(self.verify_mode),
            'created_by': to_json_value(self.created_by),
            'creation_date': a_iso_utc(self.creation_date),
            'last_update_date': a_iso_utc(self.last_update_date),
            'deletion_date': a_iso_utc(self.deletion_date),
        }

    def serialize_summary(self) -> dict:
        return {'id_attendance_record': self.id_attendance_record}
