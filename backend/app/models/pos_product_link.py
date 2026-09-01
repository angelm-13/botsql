"""Enlace entre un producto del nucleo y el del punto de venta.

El POS corre contra su propia base, asi que sus productos no son filas de
`product`: son otro sistema con sus propios identificadores. Sin un enlace, «un
solo inventario» se queda en la intencion, porque una venta del POS no tiene
forma de decir que producto del nucleo descontar.

El enlace es explicito y no por nombre. Emparejar por descripcion parece comodo
hasta que dos productos se llaman casi igual y las ventas empiezan a descontar
del renglon equivocado sin que nada avise.

Un producto del POS sin enlace no descuenta, y eso se reporta. Es preferible a
inventar una correspondencia: un inventario que descuenta del producto
equivocado es peor que uno que no descuenta, porque el primero se ve sano.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PosProductLink(Base):
    __tablename__ = "pos_product_link"
    __table_args__ = (
        # Un producto del POS descuenta de uno solo del nucleo: dos enlaces
        # dejarian la venta descontando dos veces.
        UniqueConstraint("pos_product_id", name="uq_pos_product_link"),
        Index("idx_pos_product_link_product", "id_product"),
    )

    id_pos_product_link: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_product: Mapped[int] = mapped_column(ForeignKey("product.id_product"), nullable=False)

    # UUID del producto en la base del POS. Texto y no referencia: es de otro
    # sistema y esta base no lo puede validar.
    pos_product_id: Mapped[str] = mapped_column(String(64), nullable=False)
    pos_product_name: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Donde se descuenta en el nucleo lo que el POS vende.
    id_location: Mapped[int] = mapped_column(ForeignKey("location.id_location"), nullable=False)

    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    last_update_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
    deletion_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {
            "id_pos_product_link": self.id_pos_product_link,
            "id_product": self.id_product,
            "pos_product_id": self.pos_product_id,
            "pos_product_name": self.pos_product_name,
            "id_location": self.id_location,
        }
