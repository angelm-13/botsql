from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class LogisticsEvidence(Base):
    __tablename__ = 'logistics_evidence'
    __table_args__ = (
        CheckConstraint('latitude IS NULL OR latitude BETWEEN -90 AND 90', name='ck_logistics_evidence_latitude'),
        CheckConstraint('longitude IS NULL OR longitude BETWEEN -180 AND 180', name='ck_logistics_evidence_longitude'),
    )

    id_logistics_evidence: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_logistics_trip: Mapped[int] = mapped_column(ForeignKey('logistics_trip.id_logistics_trip'), nullable=False)
    evidence_type: Mapped[str] = mapped_column(String(80), nullable=False)
    photo_path: Mapped[str | None] = mapped_column(String(300), nullable=True)
    signature_path: Mapped[str | None] = mapped_column(String(300), nullable=True)
    source_document_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7), nullable=True)
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7), nullable=True)
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    captured_by: Mapped[int | None] = mapped_column(ForeignKey('user.id_user'), nullable=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    created_by: Mapped[int] = mapped_column(ForeignKey('user.id_user'), nullable=False)
    creation_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
    deletion_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {
            column.name: float(value) if isinstance(value, Decimal) else value.isoformat() if isinstance(value, datetime) else value
            for column in self.__table__.columns
            if (value := getattr(self, column.name)) is not None
        }

    def serialize_summary(self) -> dict:
        return {'id_logistics_evidence': self.id_logistics_evidence, 'evidence_type': self.evidence_type}