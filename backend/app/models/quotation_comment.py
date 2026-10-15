from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.utils.tiempo import a_iso_utc


class QuotationComment(Base):
    __tablename__ = "quotation_comment"

    id_quotation_comment: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_invoice: Mapped[int] = mapped_column(ForeignKey("invoice.id_invoice"), nullable=False, index=True)
    id_user: Mapped[int] = mapped_column(ForeignKey("user.id_user"), nullable=False)
    message: Mapped[str] = mapped_column(String(1000), nullable=False)
    creation_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    def serialize(self):
        return {
            "id_quotation_comment": self.id_quotation_comment,
            "id_invoice": self.id_invoice,
            "message": self.message,
            "creation_date": a_iso_utc(self.creation_date),
        }