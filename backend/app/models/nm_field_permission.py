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


class NmFieldPermission(Base):
    __tablename__ = 'nm_field_permission'

    id_nm_field_permission: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    id_field: Mapped[int] = mapped_column(Integer, ForeignKey('field.id_field'), nullable=False)
    id_permission: Mapped[int] = mapped_column(Integer, ForeignKey('permission.id_permission'), nullable=False)
    control_type: Mapped[object] = mapped_column(Enum('1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', name='nm_field_permission_control_type_enum', native_enum=False, validate_strings=True, create_constraint=True), nullable=False)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)
    # Cuando toco la fila el Gestor de roles; ver el mismo campo en EntityPermission.
    ajustado_por_gestor: Mapped[object] = mapped_column(
        DateTime, nullable=True, default=func.now(), onupdate=func.now()
    )

    def serialize(self) -> dict:
        return {
            'id_nm_field_permission': to_json_value(self.id_nm_field_permission),
            'id_field': to_json_value(self.id_field),
            'id_permission': to_json_value(self.id_permission),
            'control_type': to_json_value(self.control_type),
            'created_by': to_json_value(self.created_by),
            'creation_date': a_iso_utc(self.creation_date),
            'last_update_date': a_iso_utc(self.last_update_date),
            'deletion_date': a_iso_utc(self.deletion_date),
        }

    def serialize_summary(self) -> dict:
        return {'id_nm_field_permission': self.id_nm_field_permission}
