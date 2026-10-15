"""El lote y su caducidad, para lo que se compra para vender.

Que resuelve
------------
Un saldo de 300 sacos de cemento no dice cuando caduca ninguno. Con eso, lo que
se vence se descubre en el anaquel, y quien lo descubre ya no puede hacer nada:
ni devolverlo al proveedor, ni sacarlo antes, ni dejar de comprar tanto.

El lote es lo que le pone fecha a una parte del saldo:

    300 sacos = lote L-441 (120, vence 2027-03-01)
              + lote L-508 (180, vence 2027-09-15)

Y con eso se puede sacar primero lo que vence primero, que es el unico orden de
salida que reduce la merma por caducidad.

Tres tablas y por que cada una
------------------------------
`inventory_lot` es el lote: producto, codigo del proveedor y fecha. Nada de
cantidades, porque un lote se reparte entre ubicaciones.

`inventory_lot_balance` es cuanto queda de ese lote en cada sitio. Se podria
derivar sumando el libro, y se guarda por lo mismo que `inventory_stock`: sin
saldo guardado, cada consulta de "que hay" recorre el libro entero.

`nm_inventory_ledger_lot` dice de que lotes salio cada movimiento. Hace falta
porque una salida de 30 puede cubrirse con tres lotes, y el libro escribe UN
renglon por movimiento: sin este desglose, el renglon diria que salieron 30 sin
decir de donde, y el rastro se corta justo donde importa.

Que NO lleva
------------
Costo. Se decidio dejarlo fuera a proposito: valuar el almacen es otra cosa -pide
costo promedio o FIFO, y decidir cual- y meterla aqui a medias daria una cifra
que parece un costo sin serlo.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Date, DateTime, ForeignKey, Index, Integer, String, func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.utils.tiempo import a_iso_utc


class InventoryLot(Base):
    """Un lote: lo que llego junto y caduca junto."""

    __tablename__ = "inventory_lot"
    __table_args__ = (
        Index("idx_inventory_lot_product", "id_product"),
        Index("idx_inventory_lot_expiry", "expiry_date"),
    )

    id_inventory_lot: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    id_product: Mapped[int] = mapped_column(
        ForeignKey("product.id_product"), nullable=False
    )
    # El codigo que trae el proveedor. Es la unica forma de ligar lo que esta en
    # el anaquel con lo que dice la factura de compra cuando hay un reclamo.
    lot_code: Mapped[str] = mapped_column(String(60), nullable=False)
    # Nulo a proposito: no todo caduca. Un lote sin fecha se surte al final,
    # porque uno con fecha siempre es mas urgente.
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    received_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    note: Mapped[str | None] = mapped_column(String(250), nullable=True)

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
            "id_inventory_lot": self.id_inventory_lot,
            "id_product": self.id_product,
            "lot_code": self.lot_code,
            "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
            "received_on": self.received_on.isoformat() if self.received_on else None,
            "note": self.note,
            "created_by": self.created_by,
            "creation_date": a_iso_utc(self.creation_date),
            "deletion_date": a_iso_utc(self.deletion_date),
        }


class InventoryLotBalance(Base):
    """Cuanto queda de un lote en una ubicacion.

    Un lote se reparte: llegan 300 sacos y 120 se quedan en la nave y 180 se
    suben al rack. Sin el desglose por sitio, "sacar primero lo que vence antes"
    mandaria a buscar a la ubicacion equivocada.
    """

    __tablename__ = "inventory_lot_balance"
    __table_args__ = (
        Index("idx_inventory_lot_balance_lot", "id_inventory_lot"),
        Index("idx_inventory_lot_balance_location", "id_location"),
    )

    id_inventory_lot_balance: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    id_inventory_lot: Mapped[int] = mapped_column(
        ForeignKey("inventory_lot.id_inventory_lot"), nullable=False
    )
    id_location: Mapped[int] = mapped_column(
        ForeignKey("location.id_location"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    last_update_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    def serialize(self) -> dict:
        return {
            "id_inventory_lot_balance": self.id_inventory_lot_balance,
            "id_inventory_lot": self.id_inventory_lot,
            "id_location": self.id_location,
            "quantity": int(self.quantity or 0),
        }


class NmInventoryLedgerLot(Base):
    """De que lotes movio cada renglon del libro.

    Una salida de 30 se puede cubrir con tres lotes, y el libro escribe un
    renglon por movimiento. Sin este desglose el renglon diria que salieron 30 y
    no de donde, que es justo lo que hace falta cuando el proveedor pregunta por
    su lote.

    Es de solo agregado, igual que el libro: un movimiento no se corrige, se
    contra-registra.
    """

    __tablename__ = "nm_inventory_ledger_lot"
    __table_args__ = (
        Index("idx_nm_inventory_ledger_lot_ledger", "id_inventory_ledger"),
        Index("idx_nm_inventory_ledger_lot_lot", "id_inventory_lot"),
    )

    id_nm_inventory_ledger_lot: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    id_inventory_ledger: Mapped[int] = mapped_column(
        ForeignKey("inventory_ledger.id_inventory_ledger"), nullable=False
    )
    id_inventory_lot: Mapped[int] = mapped_column(
        ForeignKey("inventory_lot.id_inventory_lot"), nullable=False
    )
    # Con el mismo signo que el movimiento: negativo si salio.
    quantity_delta: Mapped[int] = mapped_column(Integer, nullable=False)

    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    def serialize(self) -> dict:
        return {
            "id_nm_inventory_ledger_lot": self.id_nm_inventory_ledger_lot,
            "id_inventory_ledger": self.id_inventory_ledger,
            "id_inventory_lot": self.id_inventory_lot,
            "quantity_delta": int(self.quantity_delta or 0),
        }
