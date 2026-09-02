from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def _json_value(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


class LaboratoryEquipment(Base):
    __tablename__ = "laboratory_equipment"
    __table_args__ = (UniqueConstraint("id_proyect", "id_customer_supplier", "serial_number", name="uq_laboratory_equipment_owner_serial"),)

    id_laboratory_equipment: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_proyect: Mapped[int] = mapped_column(Integer, ForeignKey("proyect.id_proyect"), nullable=False, index=True)
    id_customer_supplier: Mapped[int] = mapped_column(Integer, ForeignKey("customer_supplier.id_customer_supplier"), nullable=False, index=True)
    equipment_type: Mapped[str] = mapped_column(String(100), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    serial_number: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("user.id_user"), nullable=False)
    creation_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {column.name: _json_value(getattr(self, column.name)) for column in self.__table__.columns}

    def serialize_summary(self) -> dict:
        return {"id_laboratory_equipment": self.id_laboratory_equipment, "equipment_type": self.equipment_type, "serial_number": self.serial_number}


class LaboratoryServiceOrder(Base):
    __tablename__ = "laboratory_service_order"
    __table_args__ = (UniqueConstraint("id_proyect", "folio", name="uq_laboratory_service_order_project_folio"),)

    id_laboratory_service_order: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_proyect: Mapped[int] = mapped_column(Integer, ForeignKey("proyect.id_proyect"), nullable=False, index=True)
    folio: Mapped[str] = mapped_column(String(80), nullable=False)
    id_laboratory_equipment: Mapped[int] = mapped_column(Integer, ForeignKey("laboratory_equipment.id_laboratory_equipment"), nullable=False, index=True)
    id_customer_supplier: Mapped[int] = mapped_column(Integer, ForeignKey("customer_supplier.id_customer_supplier"), nullable=False, index=True)
    id_logistics_contact: Mapped[int | None] = mapped_column(Integer, ForeignKey("logistics_contact.id_logistics_contact"), nullable=True)
    contact_name: Mapped[str] = mapped_column(String(150), nullable=False)
    contact_email: Mapped[str | None] = mapped_column(String(100), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    delivered_accessories: Mapped[str | None] = mapped_column(Text, nullable=True)
    reception_condition: Mapped[str | None] = mapped_column(Text, nullable=True)
    reported_failure: Mapped[str] = mapped_column(Text, nullable=False)
    technical_diagnosis: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommended_repair: Mapped[str | None] = mapped_column(Text, nullable=True)
    work_performed: Mapped[str | None] = mapped_column(Text, nullable=True)
    id_technician: Mapped[int | None] = mapped_column(Integer, ForeignKey("user.id_user"), nullable=True, index=True)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="normal", server_default="normal")
    estimated_budget: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    final_cost: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    estimated_repair_time: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reception_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    diagnosis_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    estimated_delivery_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    actual_delivery_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="received", server_default="received", index=True)
    observations: Mapped[str | None] = mapped_column(Text, nullable=True)
    service_conditions: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("user.id_user"), nullable=False)
    creation_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {column.name: _json_value(getattr(self, column.name)) for column in self.__table__.columns}

    def serialize_summary(self) -> dict:
        return {"id_laboratory_service_order": self.id_laboratory_service_order, "folio": self.folio, "status": self.status}


class LaboratoryServiceOrderStatusHistory(Base):
    __tablename__ = "laboratory_service_order_status_history"

    id_laboratory_service_order_status_history: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_laboratory_service_order: Mapped[int] = mapped_column(Integer, ForeignKey("laboratory_service_order.id_laboratory_service_order"), nullable=False, index=True)
    previous_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    new_status: Mapped[str] = mapped_column(String(30), nullable=False)
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("user.id_user"), nullable=False)
    creation_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    def serialize(self) -> dict:
        return {column.name: _json_value(getattr(self, column.name)) for column in self.__table__.columns}

    def serialize_summary(self) -> dict:
        return {"id_laboratory_service_order_status_history": self.id_laboratory_service_order_status_history, "new_status": self.new_status}