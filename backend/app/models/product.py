from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, BigInteger, SmallInteger, Boolean, Date, DateTime, Float, Numeric, ForeignKey, Text, JSON, Enum, LargeBinary, UniqueConstraint, func, text
from app.models.base import Base


def to_json_value(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.hex()
    return value


class Product(Base):
    __tablename__ = 'product'

    id_product: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    id_invoice: Mapped[int] = mapped_column(Integer, ForeignKey('invoice.id_invoice'), nullable=False)
    id_location: Mapped[int] = mapped_column(Integer, ForeignKey('location.id_location'), nullable=False)
    id_material: Mapped[int] = mapped_column(Integer, ForeignKey('material.id_material'), nullable=False)
    gross_price: Mapped[float] = mapped_column(Numeric(10,2), nullable=True)
    color: Mapped[object] = mapped_column(String(100), nullable=True)
    is_directly_related_to_product_service: Mapped[bool] = mapped_column(Boolean, nullable=False)
    # Texto libre, historico. Se conserva porque es lo que se capturo hasta
    # ahora y tirarlo seria perder informacion; lo nuevo va en
    # `id_inventory_status`.
    product_status: Mapped[object] = mapped_column(String(20), nullable=True)
    # El estatus del producto, contra catalogo: nuevo, usado, en reparacion,
    # danado, retirado.
    #
    # No hay tabla nueva porque ya existe: `inventory_status` es un catalogo
    # de estados con `entity_scope`, y los del producto viven con
    # `entity_scope = 'product'`. Con la columna de texto no se podia
    # filtrar -cada quien escribia "Nuevo", "nuevo" o "n"-.
    id_inventory_status: Mapped[int | None] = mapped_column(
        Integer, ForeignKey('inventory_status.id_inventory_status'), nullable=True)
    path_imagen: Mapped[object] = mapped_column(String(100), nullable=True)
    product_code: Mapped[object] = mapped_column(String(30), nullable=True)
    note: Mapped[object] = mapped_column(String(300), nullable=True)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)
    descripcion: Mapped[object] = mapped_column(String(250), nullable=True)
    cantidad: Mapped[int] = mapped_column(Integer, nullable=True)
    # Como se lleva este producto en el almacen. `fungible` se cuenta -es lo que
    # el sistema hacia siempre, y sigue siendo el valor por omision-;
    # `serializado` da una fila por unidad en `inventory_asset`, con estado y
    # responsable, para lo que hay que rastrear pieza por pieza: herramienta,
    # equipo, activo de uso.
    tracking_mode: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'fungible'")
    )
    # Para que sirve en el almacen. `mercancia` se compra para venderse -es el
    # valor por omision, que es como se ha usado el almacen hasta ahora-;
    # `uso_interno` es herramienta, equipo o consumible de la empresa, que no se
    # vende nunca: sale para usarse, prestarse o consumirse.
    #
    # Sin esta distincion una herramienta prestada y un producto vendido se
    # veian igual en el saldo, y nada impedia facturar la venta de un taladro
    # propio.
    stock_purpose: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'mercancia'")
    )
    id_marca: Mapped[int] = mapped_column(Integer, nullable=True)
    id_familia: Mapped[int] = mapped_column(Integer, nullable=True)

    def serialize(self) -> dict:
        return {
            'id_product': to_json_value(self.id_product),
            'id_invoice': to_json_value(self.id_invoice),
            'id_location': to_json_value(self.id_location),
            'id_material': to_json_value(self.id_material),
            'gross_price': to_json_value(self.gross_price),
            'color': to_json_value(self.color),
            'is_directly_related_to_product_service': to_json_value(self.is_directly_related_to_product_service),
            'product_status': to_json_value(self.product_status),
            'id_inventory_status': to_json_value(self.id_inventory_status),
            'path_imagen': to_json_value(self.path_imagen),
            'product_code': to_json_value(self.product_code),
            'note': to_json_value(self.note),
            'created_by': to_json_value(self.created_by),
            'creation_date': to_json_value(self.creation_date),
            'last_update_date': to_json_value(self.last_update_date),
            'deletion_date': to_json_value(self.deletion_date),
            'descripcion': to_json_value(self.descripcion),
            'cantidad': to_json_value(self.cantidad),
            'id_marca': to_json_value(self.id_marca),
            'id_familia': to_json_value(self.id_familia),
        }

    def serialize_summary(self) -> dict:
        return {'id_product': self.id_product}
