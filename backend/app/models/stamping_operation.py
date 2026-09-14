from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class StampingOperation(Base):
    __tablename__ = "stamping_operation"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_stamping_operation_idempotency_key"),
        Index("ix_stamping_operation_invoice", "id_invoice", "creation_date"),
    )

    id_stamping_operation: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_invoice: Mapped[int] = mapped_column(ForeignKey("invoice.id_invoice"), nullable=False)
    id_proyect: Mapped[int] = mapped_column(ForeignKey("proyect.id_proyect"), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False)
    provider: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    provider_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    response_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    def serialize(self):
        return {
            "id_stamping_operation": self.id_stamping_operation,
            "id_invoice": self.id_invoice,
            "id_proyect": self.id_proyect,
            "idempotency_key": self.idempotency_key,
            "provider": self.provider,
            "status": self.status,
            "provider_reference": self.provider_reference,
            "error_code": self.error_code,
            # El diagnostico del PAC es lo que permite corregir un rechazo:
            # sin esto la API solo devolvia el codigo HTTP.
            "response_metadata": self.response_metadata,
            "creation_date": self.creation_date.isoformat() if self.creation_date else None,
            "last_update_date": self.last_update_date.isoformat() if self.last_update_date else None,
        }
