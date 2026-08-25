from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def to_json_value(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


class ProyectEvent(Base):
    __tablename__ = "proyect_event"

    id_proyect_event: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_proyect: Mapped[int] = mapped_column(Integer, ForeignKey("proyect.id_proyect"), nullable=False, index=True)
    id_task: Mapped[int | None] = mapped_column(Integer, ForeignKey("task.id_task"), nullable=True, index=True)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("user.id_user"), nullable=False, index=True)
    author_role: Mapped[str | None] = mapped_column(String(100), nullable=True)
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    previous_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    new_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    creation_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    def serialize(self) -> dict:
        return {
            "id_proyect_event": self.id_proyect_event,
            "id_proyect": self.id_proyect,
            "id_task": self.id_task,
            "created_by": self.created_by,
            "author_role": self.author_role,
            "event_type": self.event_type,
            "previous_status": self.previous_status,
            "new_status": self.new_status,
            "content": self.content,
            "reason": self.reason,
            "review_date": to_json_value(self.review_date),
            "creation_date": to_json_value(self.creation_date),
        }

    def serialize_summary(self) -> dict:
        return {"id_proyect_event": self.id_proyect_event}