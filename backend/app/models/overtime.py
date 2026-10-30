from __future__ import annotations
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Integer, String, func
from app.models.base import Base
from app.models.work_schedule import _auditoria, to_json_value

# Horas extra (migracion 20261030100000). Las reglas -que se verifica contra las
# checadas, dobles y triples, la parte exenta, cuando se pagan- viven en
# services/overtime_service.py.

AUTORIZADA, DETECTADA, MANUAL = "authorized", "detected", "manual"
PAGAR, COMPENSAR = "pay", "compensate"


class Overtime(Base):
    """Horas extra de un empleado en un dia.

    `origin`: authorized (el supervisor o RH la autorizo antes), detected (era
    tiempo no autorizado de las checadas y se aprobo) o manual (RH la capturo
    sin checadas, con motivo). `minutes` es lo autorizado; lo que se paga es lo
    autorizado con tope en lo que marcan las checadas, salvo las manuales.
    `settlement`: pay (se paga) o compensate (tiempo libre: no se paga y queda
    el comentario). `id_payroll_period` se fija al cerrar el periodo que la pago.
    """

    __tablename__ = 'overtime'
    __table_args__ = (
        CheckConstraint("origin IN ('authorized', 'detected', 'manual')", name='ck_overtime_origin'),
        CheckConstraint("settlement IN ('pay', 'compensate')", name='ck_overtime_settlement'),
        CheckConstraint('minutes > 0', name='ck_overtime_minutes'),
    )

    id_overtime: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    id_user: Mapped[int] = mapped_column(Integer, ForeignKey('user.id_user'), nullable=False)
    work_date: Mapped[object] = mapped_column(Date, nullable=False)
    minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    origin: Mapped[str] = mapped_column(String(20), nullable=False, default=AUTORIZADA, server_default=AUTORIZADA)
    settlement: Mapped[str] = mapped_column(String(20), nullable=False, default=PAGAR, server_default=PAGAR)
    notes: Mapped[str | None] = mapped_column(String(300), nullable=True)
    id_payroll_period: Mapped[int | None] = mapped_column(Integer, ForeignKey('payroll_period.id_payroll_period'),
                                                          nullable=True)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default='1')
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {'id_overtime': self.id_overtime, 'id_user': self.id_user, 'work_date': to_json_value(self.work_date),
                'minutes': self.minutes, 'origin': self.origin, 'settlement': self.settlement, 'notes': self.notes,
                'id_payroll_period': self.id_payroll_period, **_auditoria(self)}

    def serialize_summary(self) -> dict:
        return {'id_overtime': self.id_overtime}
