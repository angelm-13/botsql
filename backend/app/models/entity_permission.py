
from __future__ import annotations

from sqlalchemy import Integer, SmallInteger, String, DateTime, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class EntityPermission(Base):
    __tablename__ = "entity_permission"
    __table_args__ = (
        UniqueConstraint("id_permission", "entity_name", name="uq_entity_permission_scope"),
    )

    id_entity_permission: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_permission: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    entity_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    control_type: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=15)
    menu_location: Mapped[str] = mapped_column(String(20), nullable=False, default="sidebar")
    menu_group: Mapped[str | None] = mapped_column(String(80), nullable=True)
    menu_label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    menu_order: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object | None] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {
            "id_entity_permission": self.id_entity_permission,
            "id_permission": self.id_permission,
            "entity_name": self.entity_name,
            "control_type": self.control_type,
            "menu_location": self.menu_location,
            "menu_group": self.menu_group,
            "menu_label": self.menu_label,
            "menu_order": self.menu_order,
        }

    def serialize_summary(self) -> dict:
        return {
            "id_entity_permission": self.id_entity_permission,
            "entity_name": self.entity_name,
            "menu_location": self.menu_location,
            "menu_group": self.menu_group,
            "menu_label": self.menu_label,
            "menu_order": self.menu_order,
        }
