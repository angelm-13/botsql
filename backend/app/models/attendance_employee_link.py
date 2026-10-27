from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, DateTime, func, text
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


class AttendanceEmployeeLink(Base):
    """Que empleado del sistema es cada numero del checador."""

    __tablename__ = 'attendance_employee_link'
    __table_args__ = (
        CheckConstraint("source IN ('kronos', 'whatsapp', 'manual')", name='ck_attendance_employee_link_source'),
        # Un numero vivo se liga a un solo empleado. Mismo indice parcial que la
        # migracion 20261016110000_vinculo_checador_empleado.sql.
        Index('uq_attendance_employee_link_vivo', 'source', 'employee_no', unique=True,
              postgresql_where=text('deletion_date IS NULL'),
              sqlite_where=text('deletion_date IS NULL')),
    )

    id_attendance_employee_link: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default='kronos', server_default='kronos')
    employee_no: Mapped[str] = mapped_column(String(32), nullable=False)
    id_user: Mapped[int] = mapped_column(Integer, ForeignKey('user.id_user'), nullable=False)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {
            'id_attendance_employee_link': to_json_value(self.id_attendance_employee_link),
            'source': to_json_value(self.source),
            'employee_no': to_json_value(self.employee_no),
            'id_user': to_json_value(self.id_user),
            'created_by': to_json_value(self.created_by),
            'creation_date': a_iso_utc(self.creation_date),
            'last_update_date': a_iso_utc(self.last_update_date),
            'deletion_date': a_iso_utc(self.deletion_date),
        }

    def serialize_summary(self) -> dict:
        return {'id_attendance_employee_link': self.id_attendance_employee_link}
