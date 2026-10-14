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


class IncidentDetail(Base):
    __tablename__ = 'incident_detail'

    id_incident_detail: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    id_incident_type: Mapped[int] = mapped_column(Integer, ForeignKey('incident_type.id_incident_type'), nullable=False)
    incident_detail_name: Mapped[object] = mapped_column(String(50), nullable=False)
    incident_detail_description: Mapped[object] = mapped_column(String(200), nullable=False)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {
            'id_incident_detail': to_json_value(self.id_incident_detail),
            'id_incident_type': to_json_value(self.id_incident_type),
            'incident_detail_name': to_json_value(self.incident_detail_name),
            'incident_detail_description': to_json_value(self.incident_detail_description),
            'created_by': to_json_value(self.created_by),
            'creation_date': a_iso_utc(self.creation_date),
            'last_update_date': a_iso_utc(self.last_update_date),
            'deletion_date': a_iso_utc(self.deletion_date),
        }

    def serialize_summary(self) -> dict:
        return {'id_incident_detail': self.id_incident_detail}
