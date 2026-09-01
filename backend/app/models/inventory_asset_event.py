"""Historia de una pieza: todo lo que le paso, en orden y sin borrar nada.

Por que no basta con el estado actual
-------------------------------------
`inventory_asset.status` dice donde esta la pieza hoy. Esta tabla dice como
llego ahi. La diferencia importa cuando algo se pierde: con solo el estado
actual, una herramienta extraviada es un dato sin explicacion; con la historia
se ve quien la tuvo, cuando debio devolverla y quien la recibio antes.

Es de solo agregado, igual que `inventory_ledger`. Un renglon no se corrige
editandolo: se escribe otro que dice lo que paso despues. Editar la historia
para que cuadre es exactamente lo que vuelve inutil una bitacora.

Cada renglon guarda el antes y el despues -estado, ubicacion y responsable- en
lugar de solo el cambio. Cuesta unas columnas mas y evita tener que reconstruir
el estado sumando renglones, que es donde una consulta mal escrita empieza a
mentir.

Relacion con el libro de existencias
------------------------------------
`id_inventory_ledger` amarra el evento con el movimiento de existencia que
provoco, cuando provoco alguno. Asi se puede ir de "quien se llevo el taladro" a
"que renglon del libro lo descontó" sin adivinar por fecha.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, String, func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


# Que le paso a la pieza. Se nombran por el hecho, no por el estado al que
# llevan, porque el mismo estado se alcanza por caminos distintos: una pieza
# vuelve a `disponible` tanto de un prestamo como de una reparacion, y no es lo
# mismo.
ALTA = "alta"                    # entra al inventario
ASIGNACION = "asignacion"        # se entrega a alguien de la empresa
PRESTAMO = "prestamo"            # sale de la empresa, con fecha de regreso
DEVOLUCION = "devolucion"        # vuelve de un prestamo o una asignacion
ENVIO_REPARACION = "envio_reparacion"
REGRESO_REPARACION = "regreso_reparacion"
EXTRAVIO = "extravio"
BAJA = "baja"                    # retiro definitivo
TRASLADO = "traslado"            # cambia de ubicacion sin cambiar de estado

EVENTOS = (
    ALTA, ASIGNACION, PRESTAMO, DEVOLUCION, ENVIO_REPARACION,
    REGRESO_REPARACION, EXTRAVIO, BAJA, TRASLADO,
)


class InventoryAssetEvent(Base):
    """Un hecho en la vida de una pieza."""

    __tablename__ = "inventory_asset_event"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('alta','asignacion','prestamo','devolucion',"
            "'envio_reparacion','regreso_reparacion','extravio','baja','traslado')",
            name="ck_inventory_asset_event_type",
        ),
        # La consulta natural: la historia de esta pieza en orden.
        Index("idx_inventory_asset_event_asset", "id_inventory_asset", "id_inventory_asset_event"),
        Index("idx_inventory_asset_event_holder", "id_holder_after"),
        Index("idx_inventory_asset_event_type", "event_type"),
    )

    id_inventory_asset_event: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    id_inventory_asset: Mapped[int] = mapped_column(
        ForeignKey("inventory_asset.id_inventory_asset"), nullable=False
    )

    event_type: Mapped[str] = mapped_column(String(30), nullable=False)

    # El antes y el despues completos, para no tener que reconstruirlos.
    status_before: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status_after: Mapped[str] = mapped_column(String(20), nullable=False)
    id_location_before: Mapped[int | None] = mapped_column(
        ForeignKey("location.id_location"), nullable=True
    )
    id_location_after: Mapped[int | None] = mapped_column(
        ForeignKey("location.id_location"), nullable=True
    )
    id_holder_before: Mapped[int | None] = mapped_column(Integer, nullable=True)
    id_holder_after: Mapped[int | None] = mapped_column(Integer, nullable=True)

    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # El movimiento de existencia que este evento provoco, si provoco alguno.
    # Un traslado o una asignacion interna pueden no mover el saldo.
    id_inventory_ledger: Mapped[int | None] = mapped_column(
        ForeignKey("inventory_ledger.id_inventory_ledger"), nullable=True
    )

    # Documento o tarea que lo respalda, con la misma convencion que el libro.
    reference_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reference_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    reason: Mapped[str | None] = mapped_column(String(300), nullable=True)

    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    def serialize(self) -> dict:
        return {
            "id_inventory_asset_event": self.id_inventory_asset_event,
            "id_inventory_asset": self.id_inventory_asset,
            "event_type": self.event_type,
            "status_before": self.status_before,
            "status_after": self.status_after,
            "id_location_before": self.id_location_before,
            "id_location_after": self.id_location_after,
            "id_holder_before": self.id_holder_before,
            "id_holder_after": self.id_holder_after,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "id_inventory_ledger": self.id_inventory_ledger,
            "reference_type": self.reference_type,
            "reference_id": self.reference_id,
            "reason": self.reason,
            "created_by": self.created_by,
            "creation_date": self.creation_date.isoformat() if self.creation_date else None,
        }
