from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class LogisticsIncident(Base):
    __tablename__ = 'logistics_incident'
    __table_args__ = (
        CheckConstraint("severity IN ('baja', 'media', 'alta', 'critica')", name='ck_logistics_incident_severity'),
        CheckConstraint(
            "status IN ('abierta', 'en_proceso', 'resuelta', 'cerrada', 'cancelada')",
            name='ck_logistics_incident_status',
        ),
    )

    id_logistics_incident: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_logistics_trip: Mapped[int] = mapped_column(ForeignKey('logistics_trip.id_logistics_trip'), nullable=False)
    incident_type: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default='media', server_default='media')
    description: Mapped[str] = mapped_column(Text, nullable=False)
    responsible_user_id: Mapped[int | None] = mapped_column(ForeignKey('user.id_user'), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default='abierta', server_default='abierta')
    created_by: Mapped[int] = mapped_column(ForeignKey('user.id_user'), nullable=False)
    creation_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
    deletion_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {
            column.name: value.isoformat() if isinstance(value, datetime) else value
            for column in self.__table__.columns
            if (value := getattr(self, column.name)) is not None
        }

    def serialize_summary(self) -> dict:
        return {'id_logistics_incident': self.id_logistics_incident, 'incident_type': self.incident_type}