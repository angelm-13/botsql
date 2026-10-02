"""Lo que un proyecto necesita, antes de saber de donde sale.

Texto libre primero, catalogo despues
-------------------------------------
El almacen de Adser es de HERRAMIENTA: su catalogo de materiales son tipos de
herramienta y equipo (taladros, generadores de soldadura). Lo que un supervisor
necesita para su obra -tornillos, soldadura, discos- casi nunca esta ahi, asi que
la necesidad se describe con texto libre y el vinculo al catalogo es OPCIONAL.

Si el supervisor escribe algo que si hay en el almacen, el sistema se lo sugiere
al capturar y, si no lo vincula, el renglon sale marcado "por revisar" en la
vista de compras: alguien que conoce el almacen decide si ya existe (lo vincula)
o si de verdad hay que comprarlo (lo confirma). Nunca se oculta una necesidad
porque el texto "se parezca" a algo del catalogo: buscar por texto no es
confiable (un "esmeril angular" puede estar como "amoladora").

Por que una tabla nueva y no los renglones de factura
-----------------------------------------------------
`invoice_material_service` ya tiene material, cantidad, comprador y proveedor,
pero cuelga de una factura: lleva precios, impuestos y claves del SAT, y la
captura quien factura. Esta lista la declara el supervisor desde su proyecto, sin
pasar por facturacion. Queda una llave OPCIONAL al renglon de factura para
ligarlos despues si Adser lo pide.

La necesidad no dice como se cubre
----------------------------------
Pide "20 discos de corte", no "comprar 20 discos". De donde sale -existencia,
compra o renta- se decide despues, y lo decide quien compra. Aqui no hay
modalidad.

Puede pedir mas de lo que hay
-----------------------------
A diferencia del prevale, que es recoger material fisico y por eso no pasa de la
existencia, esta lista sirve justo para avisar que falta. Pedir de mas no es un
error: es el dato.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint, Date, DateTime, ForeignKey, Integer, String, func, text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

# Abierta: sigue haciendo falta. Cancelada: ya no se necesita (cambio de alcance,
# se consiguio por otro lado). No se borra, para que quede dicho que se pidio.
NEED_STATUSES = ("open", "cancelled")

# Que decidio quien reviso un renglon de texto libre:
#   linked  -> ya existe en el almacen; se vinculo al catalogo
#   buy     -> de verdad hay que comprarlo; se confirmo
REVIEW_RESULTS = ("linked", "buy")


def _valor(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


class ProyectMaterialNeed(Base):
    __tablename__ = "proyect_material_need"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_proyect_material_need_quantity"),
        CheckConstraint(
            "need_status IN ('open', 'cancelled')",
            name="ck_proyect_material_need_status",
        ),
        CheckConstraint(
            "review_result IS NULL OR review_result IN ('linked', 'buy')",
            name="ck_proyect_material_need_review",
        ),
        # Algo hay que decir: o se vincula al catalogo o se describe.
        CheckConstraint(
            "id_material IS NOT NULL OR (description IS NOT NULL AND description <> '')",
            name="ck_proyect_material_need_what",
        ),
    )

    id_proyect_material_need: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True)
    id_proyect: Mapped[int] = mapped_column(
        Integer, ForeignKey("proyect.id_proyect"), nullable=False, index=True)
    # Opcional: solo cuando lo pedido existe en el catalogo.
    id_material: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("material.id_material"), nullable=True, index=True)
    # Lo que se necesita, con las palabras del supervisor. Obligatoria si no hay
    # material vinculado.
    description: Mapped[str | None] = mapped_column(String(200), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(40), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    # Para cuando hace falta. Opcional: no todo se pide con fecha.
    needed_by: Mapped[date | None] = mapped_column(Date, nullable=True)
    note: Mapped[str | None] = mapped_column(String(300), nullable=True)
    need_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="open", server_default=text("'open'"))
    # La revision de un renglon de texto libre: quien, cuando y que decidio.
    review_result: Mapped[str | None] = mapped_column(String(10), nullable=True)
    reviewed_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reviewed_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Ligadura opcional con lo cotizado. Vacia hasta que alguien la pida.
    id_invoice_material_service: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("invoice_material_service.id_invoice_material_service"),
        nullable=True)
    created_by: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default=text("1"))
    creation_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {c.name: _valor(getattr(self, c.name)) for c in self.__table__.columns}
