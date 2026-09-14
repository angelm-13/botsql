from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class LogisticsBranch(Base):
    __tablename__ = 'logistics_branch'
    __table_args__ = (
        CheckConstraint("status IN ('activo', 'inactivo')", name='ck_logistics_branch_status'),
    )

    id_logistics_branch: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    series: Mapped[str | None] = mapped_column(String(30), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default='activo', server_default='activo')
    created_by: Mapped[int] = mapped_column(ForeignKey('user.id_user'), nullable=False)
    creation_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {column.name: value.isoformat() if isinstance(value, datetime) else value for column in self.__table__.columns if (value := getattr(self, column.name)) is not None}

    def serialize_summary(self) -> dict:
        return {'id_logistics_branch': self.id_logistics_branch, 'name': self.name}