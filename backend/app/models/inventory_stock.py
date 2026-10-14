from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.utils.tiempo import a_iso_utc


class InventoryStock(Base):
    """Existencia de un producto en una ubicacion concreta.

    Antes la existencia vivia en `product.cantidad`, un solo numero por
    producto, de modo que un producto no podia estar en dos almacenes. Aqui
    vive el detalle por ubicacion; `product.cantidad` se conserva como el
    total, que el servicio de inventario mantiene como la suma de estas filas.

    El almacen no es una columna: es la ubicacion ancestro cuyo tipo esta
    marcado como almacen. Asi el mismo arbol sirve para almacen, zona, rack y
    posicion sin duplicar el concepto.
    """

    __tablename__ = "inventory_stock"
    __table_args__ = (
        UniqueConstraint("id_product", "id_location", name="uq_inventory_stock_product_location"),
        CheckConstraint("quantity >= 0", name="ck_inventory_stock_quantity_non_negative"),
        Index("ix_inventory_stock_location", "id_location"),
    )

    id_inventory_stock: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_product: Mapped[int] = mapped_column(ForeignKey("product.id_product"), nullable=False)
    id_location: Mapped[int] = mapped_column(ForeignKey("location.id_location"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    def serialize(self):
        return {
            "id_inventory_stock": self.id_inventory_stock,
            "id_product": self.id_product,
            "id_location": self.id_location,
            "quantity": self.quantity,
            "created_by": self.created_by,
            "creation_date": a_iso_utc(self.creation_date),
            "last_update_date": a_iso_utc(self.last_update_date),
        }
