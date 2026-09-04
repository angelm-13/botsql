"""El tipo dentro de una familia de materiales.

Un material se define por tres cosas: su familia, su tipo y su marca.

    familia "Desarmadores" + tipo "Plano"   + marca "Truper"
    familia "Desarmadores" + tipo "De cruz" + marca "Lion Tools"

De las tres, `material` ya tenia familia y marca. El tipo vivia dentro del texto
de la descripcion, asi que se podia escribir pero no agrupar, ni filtrar, ni
contar cuantos desarmadores planos hay.

Por que el tipo cuelga de la familia
------------------------------------
"Plano" no significa nada por si mismo: es un tipo de desarmador. Con una tabla
plana de tipos, el alta de un material dejaria elegir "Cemento" de tipo "De
cruz" y nada lo impediria. Colgandolo de la familia, el desplegable solo ofrece
los tipos de la familia elegida y la combinacion absurda no se puede capturar.

El par (familia, descripcion) es unico entre los vivos: dos "Plano" en
desarmadores son el mismo tipo capturado dos veces, y con los dos vigentes la
mitad de los materiales apunta a uno y la mitad al otro.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class MaterialType(Base):
    __tablename__ = "material_type"
    __table_args__ = (
        Index("idx_material_type_family", "id_product_family"),
    )

    id_material_type: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    id_product_family: Mapped[int] = mapped_column(
        ForeignKey("product_family.id_product_family"), nullable=False
    )
    material_type_description: Mapped[str] = mapped_column(String(120), nullable=False)

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
            "id_material_type": self.id_material_type,
            "id_product_family": self.id_product_family,
            "material_type_description": self.material_type_description,
            "created_by": self.created_by,
            "creation_date": self.creation_date.isoformat() if self.creation_date else None,
            "last_update_date": (
                self.last_update_date.isoformat() if self.last_update_date else None
            ),
            "deletion_date": self.deletion_date.isoformat() if self.deletion_date else None,
        }

    def serialize_summary(self) -> dict:
        return {
            "id_material_type": self.id_material_type,
            "material_type_description": self.material_type_description,
        }
