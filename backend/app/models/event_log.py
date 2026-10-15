from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, BigInteger, SmallInteger, Boolean, Date, DateTime, Float, Numeric, ForeignKey, Text, JSON, Enum, LargeBinary, UniqueConstraint, func
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


class EventLog(Base):
    __tablename__ = 'event_log'

    id_event_log: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    table_name: Mapped[object] = mapped_column(String(50), nullable=False)
    field_name: Mapped[object] = mapped_column(String(50), nullable=False)
    # La categoria del asiento. Eran solo los tres del CRUD, y eso obligo a
    # inventar una segunda bitacora (`audit_log`) para lo que no lo era: un
    # permiso denegado, un cambio de estatus. Ver la migracion 20260911120000.
    action: Mapped[object] = mapped_column(Enum(
        'create', 'update', 'delete', 'read', 'denied', 'transition', 'custom',
        name='event_log_action_enum', native_enum=False, validate_strings=True,
        create_constraint=True), nullable=False)
    # El verbo concreto -- 'cerrado', 'mesa_cobrada' -- cuando `action` es la
    # categoria. Nulo en un asiento de CRUD, donde la categoria ya lo dice todo.
    event_detail: Mapped[object] = mapped_column(String(80), nullable=True)
    # Sube a columna desde el JSON: filtrar por proyecto era la unica consulta
    # que hacia la bitacora del restaurante, y abrir el JSON en cada fila para
    # eso no se puede indexar.
    id_proyect: Mapped[int] = mapped_column(
        Integer, ForeignKey('proyect.id_proyect'), nullable=True, index=True)
    before_value: Mapped[object] = mapped_column(JSON, nullable=False)
    after_value: Mapped[object] = mapped_column(JSON, nullable=False)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {
            'id_event_log': to_json_value(self.id_event_log),
            'table_name': to_json_value(self.table_name),
            'field_name': to_json_value(self.field_name),
            'action': to_json_value(self.action),
            'event_detail': to_json_value(self.event_detail),
            'id_proyect': to_json_value(self.id_proyect),
            'before_value': to_json_value(self.before_value),
            'after_value': to_json_value(self.after_value),
            'created_by': to_json_value(self.created_by),
            'creation_date': a_iso_utc(self.creation_date),
            'last_update_date': a_iso_utc(self.last_update_date),
            'deletion_date': a_iso_utc(self.deletion_date),
        }

    def serialize_summary(self) -> dict:
        return {'id_event_log': self.id_event_log}
