
from __future__ import annotations

from sqlalchemy import Integer, String, DateTime, JSON, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id_audit_log: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_user: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    entity_name: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    action: Mapped[str | None] = mapped_column(String(40), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())

    def serialize(self) -> dict:
        return {
            "id_audit_log": self.id_audit_log,
            "id_user": self.id_user,
            "event_type": self.event_type,
            "entity_name": self.entity_name,
            "action": self.action,
            "metadata_json": self.metadata_json,
            "creation_date": self.creation_date.isoformat() if self.creation_date else None,
        }
