from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, LargeBinary, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PacConfig(Base):
    __tablename__ = "pac_config"

    id_pac_config: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    provider: Mapped[str] = mapped_column(String(40), nullable=False, default="fake", server_default="fake")
    facturama_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    facturama_password_cipher: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    facturama_password_nonce: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    facturama_base_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    name_id: Mapped[str] = mapped_column(String(10), nullable=False, default="1", server_default="1")
    last_update_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    def serialize(self) -> dict:
        return {
            "provider": self.provider or "fake",
            "facturama_username": self.facturama_username or "",
            "facturama_base_url": self.facturama_base_url or "",
            "name_id": self.name_id or "1",
            "has_password": bool(self.facturama_password_cipher and self.facturama_password_nonce),
            "last_update_date": self.last_update_date.isoformat() if self.last_update_date else None,
        }