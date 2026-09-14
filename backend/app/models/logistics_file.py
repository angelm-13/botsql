from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class LogisticsFile(Base):
    __tablename__ = 'logistics_file'
    __table_args__ = (
        CheckConstraint("status IN ('abierto', 'facturando', 'facturado')", name='ck_logistics_file_status'),
    )

    id_logistics_file: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_customer_supplier: Mapped[int] = mapped_column(ForeignKey('customer_supplier.id_customer_supplier'), nullable=False)
    folio: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    origin: Mapped[str] = mapped_column(Text, nullable=False)
    destination: Mapped[str] = mapped_column(Text, nullable=False)
    id_logistics_branch: Mapped[int | None] = mapped_column(ForeignKey('logistics_branch.id_logistics_branch'), nullable=True)
    payment_form: Mapped[str] = mapped_column(String(10), nullable=False, default='99', server_default='99')
    payment_method: Mapped[str] = mapped_column(String(10), nullable=False, default='PUE', server_default='PUE')
    cfdi_use: Mapped[str] = mapped_column(String(10), nullable=False, default='G03', server_default='G03')
    status: Mapped[str] = mapped_column(String(20), nullable=False, default='abierto', server_default='abierto')
    id_invoice: Mapped[int | None] = mapped_column(ForeignKey('invoice.id_invoice'), nullable=True)
    last_invoice_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey('user.id_user'), nullable=False)
    creation_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {column.name: value.isoformat() if isinstance(value, datetime) else value for column in self.__table__.columns if (value := getattr(self, column.name)) is not None}

    def serialize_summary(self) -> dict:
        return {'id_logistics_file': self.id_logistics_file, 'folio': self.folio}