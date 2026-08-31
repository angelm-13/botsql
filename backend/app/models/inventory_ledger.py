from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, event, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class InventoryLedger(Base):
    __tablename__ = "inventory_ledger"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_inventory_ledger_idempotency_key"),
        Index("ix_inventory_ledger_product_created", "id_product", "creation_date"),
        Index("ix_inventory_ledger_project_created", "id_proyect", "creation_date"),
        Index("ix_inventory_ledger_location", "id_location", "creation_date"),
        Index("ix_inventory_ledger_transfer_group", "transfer_group"),
    )

    id_inventory_ledger: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_product: Mapped[int] = mapped_column(ForeignKey("product.id_product"), nullable=False)
    id_proyect: Mapped[int] = mapped_column(ForeignKey("proyect.id_proyect"), nullable=False)
    movement_type: Mapped[str] = mapped_column(String(30), nullable=False)
    quantity_delta: Mapped[int] = mapped_column(Integer, nullable=False)
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)
    # Donde ocurrio. `balance_after` sigue siendo el total del producto, para
    # que los renglones escritos antes de los almacenes sigan siendo validos;
    # `location_balance_after` es el saldo de esta ubicacion.
    id_location: Mapped[int | None] = mapped_column(ForeignKey("location.id_location"), nullable=True)
    id_location_target: Mapped[int | None] = mapped_column(ForeignKey("location.id_location"), nullable=True)
    location_balance_after: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Une la salida y la entrada de un mismo traspaso.
    transfer_group: Mapped[str | None] = mapped_column(String(36), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False)
    reference_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reference_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(250), nullable=True)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    def serialize(self):
        return {
            "id_inventory_ledger": self.id_inventory_ledger,
            "id_product": self.id_product,
            "id_proyect": self.id_proyect,
            "movement_type": self.movement_type,
            "quantity_delta": self.quantity_delta,
            "balance_after": self.balance_after,
            "id_location": self.id_location,
            "id_location_target": self.id_location_target,
            "location_balance_after": self.location_balance_after,
            "transfer_group": self.transfer_group,
            "idempotency_key": self.idempotency_key,
            "reference_type": self.reference_type,
            "reference_id": self.reference_id,
            "reason": self.reason,
            "created_by": self.created_by,
            "creation_date": self.creation_date.isoformat() if self.creation_date else None,
        }


def _reject_ledger_mutation(*_args, **_kwargs):
    raise ValueError("inventory_ledger is append-only")


event.listen(InventoryLedger, "before_update", _reject_ledger_mutation)
event.listen(InventoryLedger, "before_delete", _reject_ledger_mutation)