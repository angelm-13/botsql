from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class InvoiceFolioCounter(Base):
    """Folio consecutivo por empresa emisora (multiemisor). Ver stamping.py:
    `_next_folio`/`next_folio_if_missing` -solo se usa para asignar folio a
    quien no capturo uno propio, nunca sobreescribe un folio existente."""

    __tablename__ = "invoice_folio_counter"

    id_customer_supplier: Mapped[int] = mapped_column(
        Integer, ForeignKey("customer_supplier.id_customer_supplier"), primary_key=True)
    next_folio: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    last_update_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    def serialize(self):
        return {
            "id_customer_supplier": self.id_customer_supplier,
            "next_folio": self.next_folio,
            "last_update_date": self.last_update_date.isoformat() if self.last_update_date else None,
        }
