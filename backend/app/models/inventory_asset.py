"""Piezas que se rastrean una por una: herramienta, equipo, activo.

Por que hace falta otra tabla
-----------------------------
El inventario existente lleva **cantidades**: `inventory_stock` guarda cuantas
piezas de un producto hay en una ubicacion, y `inventory_ledger` guarda cada
movimiento. Eso alcanza para un insumo -da igual cual de los veinte costales de
cemento salio-, pero no para una herramienta.

Con solo cantidades hay preguntas que el sistema no puede contestar aunque el
saldo cuadre:

* donde esta el taladro con etiqueta A-014;
* quien se lo llevo y desde cuando;
* si esta prestado, en reparacion o si nadie lo ha visto en tres meses;
* que le ha pasado desde que se compro.

El tipo de movimiento `loan` ya existia y descontaba existencia, pero no
registraba a quien: el prestamo se veia como una resta. Aqui cada pieza es una
fila con identidad, estado y responsable, y su historia queda en
`inventory_asset_event`.

Como conviven las dos formas de llevar inventario
-------------------------------------------------
`product.tracking_mode` decide cual se aplica:

* `fungible` -maiz, cable, tornillos-: se cuenta. Es lo que ya hacia el sistema
  y sigue siendo el valor por omision, asi que nada de lo existente cambia.
* `serializado` -taladro, laptop, andamio-: cada unidad tiene su fila aqui.

Las dos formas comparten `inventory_stock`, y eso es a proposito: una pieza
disponible en su ubicacion suma al saldo igual que un insumo, de modo que quien
solo quiera saber "cuantos taladros tengo" lo lee del mismo lugar de siempre.
Cada cambio de estado escribe su movimiento en el libro, asi que las dos vistas
no se pueden separar sin que la conciliacion lo note.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, Numeric,
    String, UniqueConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


# Estados de una pieza. El nombre dice donde esta y de quien es la
# responsabilidad, que es lo que se pregunta cuando algo no aparece.
DISPONIBLE = "disponible"        # en su ubicacion, lista para usarse
EN_USO = "en_uso"               # asignada a alguien dentro de la empresa
PRESTADA = "prestada"           # fuera de la empresa, con fecha de regreso
EN_REPARACION = "en_reparacion"  # existe pero no se puede usar
EXTRAVIADA = "extraviada"       # nadie sabe donde esta
RETIRADA = "retirada"           # baja definitiva; no vuelve

ESTADOS = (DISPONIBLE, EN_USO, PRESTADA, EN_REPARACION, EXTRAVIADA, RETIRADA)

# Estados en los que la pieza sigue contando como existencia en su ubicacion.
# Solo `disponible`: en cuanto sale de la bodega o deja de servir, el saldo tiene
# que reflejarlo, porque si no el almacen dice que tiene diez taladros y en el
# estante hay tres.
ESTADOS_EN_EXISTENCIA = frozenset({DISPONIBLE})

# Desde estos estados ya no se sale. Una pieza retirada no revive; si vuelve a
# aparecer se da de alta como pieza nueva, para que su historia anterior quede
# cerrada y legible.
ESTADOS_TERMINALES = frozenset({RETIRADA})


class InventoryAsset(Base):
    """Una pieza fisica concreta, con su identidad y su estado."""

    __tablename__ = "inventory_asset"
    __table_args__ = (
        # La etiqueta es como se identifica la pieza en el mundo real: la que
        # esta pegada en la carcasa. Se exige unica porque dos herramientas con
        # la misma etiqueta vuelven inutil el rastreo.
        UniqueConstraint("asset_tag", name="uq_inventory_asset_tag"),
        CheckConstraint(
            "status IN ('disponible','en_uso','prestada','en_reparacion','extraviada','retirada')",
            name="ck_inventory_asset_status",
        ),
        # Una pieza prestada o asignada tiene responsable; una disponible no.
        # Sin esto se puede perder el rastro de quien la tiene justo cuando mas
        # importa saberlo.
        CheckConstraint(
            "(status IN ('en_uso','prestada') AND id_holder IS NOT NULL)"
            " OR (status NOT IN ('en_uso','prestada'))",
            name="ck_inventory_asset_holder_required",
        ),
        Index("idx_inventory_asset_product", "id_product"),
        Index("idx_inventory_asset_location", "id_location"),
        Index("idx_inventory_asset_status", "status"),
        Index("idx_inventory_asset_holder", "id_holder"),
        # Lo que mas se consulta: que piezas de este producto estan disponibles.
        Index("idx_inventory_asset_product_status", "id_product", "status"),
    )

    id_inventory_asset: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Que es la pieza. El producto trae la descripcion, la marca y el material;
    # aqui no se repite nada de eso.
    id_product: Mapped[int] = mapped_column(ForeignKey("product.id_product"), nullable=False)

    asset_tag: Mapped[str] = mapped_column(String(40), nullable=False)
    # El de fabrica, cuando lo trae. No se exige: hay herramienta sin serie.
    serial_number: Mapped[str | None] = mapped_column(String(120), nullable=True)

    # Donde vive. Queda en nulo cuando la pieza no esta en la empresa -prestada
    # o extraviada-, porque decir que esta en una ubicacion seria falso.
    id_location: Mapped[int | None] = mapped_column(
        ForeignKey("location.id_location"), nullable=True
    )

    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=DISPONIBLE)

    # Quien responde por ella ahora. Es el dato que convierte "falta un taladro"
    # en "el taladro lo tiene tal persona desde tal dia".
    id_holder: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Cuando deberia volver. Permite listar lo vencido sin revisar pieza por
    # pieza, que es la unica forma de que un prestamo no se vuelva permanente.
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    acquired_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    acquisition_cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)

    note: Mapped[str | None] = mapped_column(String(300), nullable=True)

    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    last_update_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
    deletion_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    @property
    def cuenta_como_existencia(self) -> bool:
        return self.status in ESTADOS_EN_EXISTENCIA

    def serialize(self) -> dict:
        return {
            "id_inventory_asset": self.id_inventory_asset,
            "id_product": self.id_product,
            "asset_tag": self.asset_tag,
            "serial_number": self.serial_number,
            "id_location": self.id_location,
            "status": self.status,
            "id_holder": self.id_holder,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "acquired_on": self.acquired_on.isoformat() if self.acquired_on else None,
            # El importe viaja como cadena y no como numero de punto flotante:
            # es dinero, y sumar flotantes en el cliente desajusta centavos.
            "acquisition_cost": (
                format(self.acquisition_cost, "f") if self.acquisition_cost is not None else None
            ),
            "note": self.note,
            "counts_as_stock": self.cuenta_como_existencia,
            "created_by": self.created_by,
            "creation_date": self.creation_date.isoformat() if self.creation_date else None,
        }
