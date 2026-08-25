from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class LogisticsQuotation(Base):
    __tablename__ = 'logistics_quotation'
    __table_args__ = (
        CheckConstraint('kilometers >= 0', name='ck_logistics_quotation_kilometers'),
        CheckConstraint('maneuvers >= 0', name='ck_logistics_quotation_maneuvers'),
        CheckConstraint('storage >= 0', name='ck_logistics_quotation_storage'),
        CheckConstraint('total >= 0', name='ck_logistics_quotation_total'),
        CheckConstraint(
            "status IN ('borrador', 'enviada', 'aceptada', 'rechazada', 'vencida', 'cancelada')",
            name='ck_logistics_quotation_status',
        ),
    )

    id_logistics_quotation: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_customer_supplier: Mapped[int] = mapped_column(
        ForeignKey('customer_supplier.id_customer_supplier'), nullable=False
    )
    folio: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    service_type: Mapped[str] = mapped_column(String(100), nullable=False)
    origin: Mapped[str] = mapped_column(Text, nullable=False)
    destination: Mapped[str] = mapped_column(Text, nullable=False)
    cargo_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    unit_required: Mapped[str | None] = mapped_column(String(120), nullable=True)
    kilometers: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0, server_default='0')
    maneuvers: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0, server_default='0')
    storage: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0, server_default='0')
    additional_services: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, 'postgresql'), nullable=False, default=dict, server_default='{}'
    )
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0, server_default='0')
    source_branch_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default='borrador', server_default='borrador')
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
        return {'id_logistics_quotation': self.id_logistics_quotation, 'folio': self.folio}