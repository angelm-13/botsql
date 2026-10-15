from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, BigInteger, SmallInteger, Boolean, Date, DateTime, Float, Numeric, ForeignKey, Text, JSON, Enum, LargeBinary, UniqueConstraint, func
from app.models.base import Base
from app.utils.tiempo import a_iso_utc


def to_json_value(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.hex()
    return value


class Material(Base):
    __tablename__ = 'material'

    id_material: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    material_description: Mapped[object] = mapped_column(String(200), nullable=False)
    id_unit: Mapped[int] = mapped_column(Integer, ForeignKey('unit.id_unit'), nullable=False)
    id_brand: Mapped[int] = mapped_column(Integer, ForeignKey('brand.id_brand'), nullable=False)
    id_product_family: Mapped[int] = mapped_column(Integer, ForeignKey('product_family.id_product_family'), nullable=False)
    # El tercer eje del material, junto a la familia y la marca:
    # familia "Desarmadores" + tipo "Plano" + marca "Truper".
    #
    # Nullable porque los materiales que ya existen no tienen tipo y no se
    # les puede inventar uno; se captura cuando alguien los edite. El tipo
    # cuelga de la familia, asi que tiene que ser uno de los de
    # `id_product_family` -lo comprueba el servicio, que es donde se puede
    # dar un error que diga que corregir-.
    id_material_type: Mapped[int | None] = mapped_column(
        Integer, ForeignKey('material_type.id_material_type'), nullable=True)
    # Foto del material, la que heredan los productos que no traen la suya.
    # Misma forma que `product.path_imagen`: `uploads/products/m_<id>.<ext>`.
    path_imagen: Mapped[object] = mapped_column(String(100), nullable=True)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {
            'id_material': to_json_value(self.id_material),
            'material_description': to_json_value(self.material_description),
            'id_unit': to_json_value(self.id_unit),
            'id_brand': to_json_value(self.id_brand),
            'id_product_family': to_json_value(self.id_product_family),
            'id_material_type': to_json_value(self.id_material_type),
            'path_imagen': to_json_value(self.path_imagen),
            'created_by': to_json_value(self.created_by),
            'creation_date': a_iso_utc(self.creation_date),
            'last_update_date': a_iso_utc(self.last_update_date),
            'deletion_date': a_iso_utc(self.deletion_date),
        }

    def serialize_summary(self) -> dict:
        return {'id_material': self.id_material}
