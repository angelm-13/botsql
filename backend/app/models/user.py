from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, BigInteger, SmallInteger, Boolean, Date, DateTime, Float, Numeric, ForeignKey, Text, JSON, Enum, LargeBinary, UniqueConstraint, func
from app.models.base import Base


def to_json_value(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.hex()
    return value


class User(Base):
    __tablename__ = 'user'
    __table_args__ = (UniqueConstraint('username', name='uq_user_username'),)

    id_user: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    date_born: Mapped[object] = mapped_column(DateTime, nullable=True)
    date_start: Mapped[object] = mapped_column(DateTime, nullable=True)
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)
    email: Mapped[object] = mapped_column(String(100), nullable=True)
    first_name: Mapped[object] = mapped_column(String(50), nullable=True)
    id_permission: Mapped[int] = mapped_column(Integer, ForeignKey('permission.id_permission'), nullable=False)
    full_name: Mapped[object] = mapped_column(String(150), nullable=False)
    id_proyect: Mapped[int] = mapped_column(Integer, ForeignKey('proyect.id_proyect'), nullable=False)
    last_name_father: Mapped[object] = mapped_column(String(50), nullable=True)
    last_name_mother: Mapped[object] = mapped_column(String(50), nullable=True)
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    national_id: Mapped[object] = mapped_column(String(50), nullable=True)
    password: Mapped[object] = mapped_column(String(256), nullable=True)
    principal_phone: Mapped[object] = mapped_column(String(15), nullable=True)
    secundary_phone: Mapped[object] = mapped_column(String(15), nullable=True)
    ssn: Mapped[object] = mapped_column(String(50), nullable=True)
    supervisor: Mapped[int] = mapped_column(Integer, nullable=False)
    base_salary: Mapped[float] = mapped_column(Numeric(12,2), nullable=True)
    hire_date: Mapped[object] = mapped_column(Date, nullable=True)
    id_status: Mapped[int] = mapped_column(Integer, ForeignKey('status.id_status'), nullable=False)
    tax_id: Mapped[object] = mapped_column(String(50), nullable=True)
    title: Mapped[object] = mapped_column(String(50), nullable=True)
    user_type: Mapped[object] = mapped_column(Enum('admin', 'client', 'supplier', 'employee', 'web_shopper', name='user_user_type_enum', native_enum=False, validate_strings=True, create_constraint=True), nullable=True)
    username: Mapped[object] = mapped_column(String(50), nullable=True)
    puesto: Mapped[object] = mapped_column(String(50), nullable=True)
    is_employee: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default='false')
    accepts_marketing: Mapped[bool] = mapped_column(Boolean, nullable=True)

    def serialize(self) -> dict:
        return {
            'id_user': to_json_value(self.id_user),
            'created_by': to_json_value(self.created_by),
            'creation_date': to_json_value(self.creation_date),
            'date_born': to_json_value(self.date_born),
            'date_start': to_json_value(self.date_start),
            'deletion_date': to_json_value(self.deletion_date),
            'email': to_json_value(self.email),
            'first_name': to_json_value(self.first_name),
            'id_permission': to_json_value(self.id_permission),
            'full_name': to_json_value(self.full_name),
            'id_proyect': to_json_value(self.id_proyect),
            'last_name_father': to_json_value(self.last_name_father),
            'last_name_mother': to_json_value(self.last_name_mother),
            'last_update_date': to_json_value(self.last_update_date),
            'national_id': to_json_value(self.national_id),
            'principal_phone': to_json_value(self.principal_phone),
            'secundary_phone': to_json_value(self.secundary_phone),
            'ssn': to_json_value(self.ssn),
            'supervisor': to_json_value(self.supervisor),
            'base_salary': to_json_value(self.base_salary),
            'hire_date': to_json_value(self.hire_date),
            'id_status': to_json_value(self.id_status),
            'tax_id': to_json_value(self.tax_id),
            'title': to_json_value(self.title),
            'user_type': to_json_value(self.user_type),
            'username': to_json_value(self.username),
            'puesto': to_json_value(self.puesto),
            'is_employee': to_json_value(self.is_employee),
            'accepts_marketing': to_json_value(self.accepts_marketing),
        }

    def serialize_summary(self) -> dict:
        return {'id_user': self.id_user}
