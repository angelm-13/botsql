from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class LogisticsInventory(Base):
    __tablename__ = 'logistics_inventory'
    __table_args__ = (
        CheckConstraint('quantity >= 0', name='ck_logistics_inventory_quantity'),
        CheckConstraint(
            "status IN ('activo', 'pendiente_surtido', 'surtido', 'inactivo')",
            name='ck_logistics_inventory_status',
        ),
    )

    id_logistics_inventory: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_customer_supplier: Mapped[int] = mapped_column(ForeignKey('customer_supplier.id_customer_supplier'), nullable=False)
    id_logistics_location: Mapped[int] = mapped_column(ForeignKey('logistics_location.id_logistics_location'), nullable=False)
    # El producto del almacen propio que representa esta mercancia, y la
    # ubicacion del nucleo contra la que se mueve. Nulos mientras nadie los
    # empareje: sin enlace la fila sigue como hasta hoy y no toca el nucleo.
    # Ver `services/logistics_inventory_bridge.py`.
    id_product: Mapped[int | None] = mapped_column(
        ForeignKey('product.id_product'), nullable=True, index=True)
    id_core_location: Mapped[int | None] = mapped_column(
        ForeignKey('location.id_location'), nullable=True)
    sku: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(300), nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False, default=0, server_default='0')
    lot: Mapped[str | None] = mapped_column(String(100), nullable=True)
    serial_number: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default='activo', server_default='activo')
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {
            column.name: float(value) if isinstance(value, Decimal) else value.isoformat() if isinstance(value, datetime) else value
            for column in self.__table__.columns
            if (value := getattr(self, column.name)) is not None
        }

    def serialize_summary(self) -> dict:
        return {'id_logistics_inventory': self.id_logistics_inventory, 'sku': self.sku}