"""Las caracteristicas que una familia declara, y los valores que un material da.

El problema
-----------
Un material se define por su familia, su tipo y su marca, y con eso se llega
hasta "desarmador Truper plano". Lo que faltaba era el resto: el largo, el
material del mango, el calibre, los litros. Hoy eso se escribia dentro de la
descripcion -"Desarmador plano 6 pulgadas mango de goma"- asi que se podia leer
pero no agrupar, ni filtrar, ni contar cuantos de 6 pulgadas hay.

Por que no son columnas
-----------------------
Porque cada familia pide otras. Un desarmador tiene largo y mango; un cable
tiene calibre y metros; la pintura tiene litros y acabado. Con columnas fijas la
tabla acaba con veinte columnas, dieciocho vacias en cada renglon, y aun asi
falta la de la familia que entre manana.

Por que no una columna JSON
---------------------------
Porque nadie declararia que campos aplican, asi que cada quien escribiria la
llave como quisiera -"largo", "longitud", "tamano"- y filtrar dejaria de ser
fiable. Es el mismo problema que tenia `product_status` cuando era texto libre.

Como queda
----------
La FAMILIA declara sus caracteristicas -`material_attribute`- y el material las
llena -`nm_material_attribute`-. Es el mismo patron que ya sigue el tipo: cuelga
de la familia, asi que el alta de un material solo ofrece las caracteristicas de
su familia y la combinacion absurda no se puede capturar.

Las tres formas de un valor
---------------------------
`data_type` dice como se lee, y de eso depende cual columna de valor se llena:

  * `texto`  -> `value_text`. Lo que no se puede acotar de antemano;
  * `numero` -> `value_text` y `value_number`. El numero va aparte para que
    "de 6 pulgadas o mas" sea una comparacion y no una comparacion de cadenas,
    donde "10" es menor que "6";
  * `lista`  -> `value_text` y `id_material_attribute_option`. Los valores
    permitidos se declaran, asi que no acaban existiendo "Plano", "plano" y
    "PLANO" como tres acabados distintos.

`value_text` se llena SIEMPRE, en los tres casos: es el valor como se muestra, y
tenerlo evita que pintar una lista de caracteristicas dependa de resolver de que
tipo era cada una.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


# Como se lee el valor de una caracteristica.
TEXTO = "texto"
NUMERO = "numero"
LISTA = "lista"
TIPOS_DE_DATO = (TEXTO, NUMERO, LISTA)


class MaterialAttribute(Base):
    """Una caracteristica que la familia declara. No es un valor: es el campo."""

    __tablename__ = "material_attribute"
    __table_args__ = (
        Index("idx_material_attribute_family", "id_product_family"),
    )

    id_material_attribute: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    id_product_family: Mapped[int] = mapped_column(
        ForeignKey("product_family.id_product_family"), nullable=False
    )
    attribute_name: Mapped[str] = mapped_column(String(80), nullable=False)
    data_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # La unidad en que se captura, cuando el numero solo no dice nada: 6 de que.
    unit_label: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

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
            "id_material_attribute": self.id_material_attribute,
            "id_product_family": self.id_product_family,
            "attribute_name": self.attribute_name,
            "data_type": self.data_type,
            "unit_label": self.unit_label,
            "is_required": bool(self.is_required),
            "sort_order": self.sort_order,
            "created_by": self.created_by,
            "creation_date": self.creation_date.isoformat() if self.creation_date else None,
            "last_update_date": (
                self.last_update_date.isoformat() if self.last_update_date else None
            ),
            "deletion_date": self.deletion_date.isoformat() if self.deletion_date else None,
        }


class MaterialAttributeOption(Base):
    """Un valor permitido de una caracteristica de tipo lista.

    Existe para que "acabado: mate" no compita con "Mate" y "MATE". Sin valores
    acotados, agrupar por acabado devuelve tres grupos donde hay uno, y ese es
    justo el fallo que ya se corrigio en el estatus del producto.
    """

    __tablename__ = "material_attribute_option"
    __table_args__ = (
        Index("idx_material_attribute_option_attribute", "id_material_attribute"),
    )

    id_material_attribute_option: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    id_material_attribute: Mapped[int] = mapped_column(
        ForeignKey("material_attribute.id_material_attribute"), nullable=False
    )
    option_value: Mapped[str] = mapped_column(String(120), nullable=False)
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

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
            "id_material_attribute_option": self.id_material_attribute_option,
            "id_material_attribute": self.id_material_attribute,
            "option_value": self.option_value,
            "sort_order": self.sort_order,
            "deletion_date": self.deletion_date.isoformat() if self.deletion_date else None,
        }


class NmMaterialAttribute(Base):
    """El valor que un material da a una caracteristica de su familia.

    Un material tiene a lo mas un valor por caracteristica: dos filas de "largo"
    para el mismo desarmador son el mismo dato capturado dos veces, y con las dos
    vivas no hay forma de saber cual vale.
    """

    __tablename__ = "nm_material_attribute"
    __table_args__ = (
        Index("idx_nm_material_attribute_material", "id_material"),
        Index("idx_nm_material_attribute_attribute", "id_material_attribute"),
    )

    id_nm_material_attribute: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    id_material: Mapped[int] = mapped_column(
        ForeignKey("material.id_material"), nullable=False
    )
    id_material_attribute: Mapped[int] = mapped_column(
        ForeignKey("material_attribute.id_material_attribute"), nullable=False
    )
    # El valor como se muestra. Se llena siempre, sea del tipo que sea.
    value_text: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # El numero aparte, para que "6 o mas" sea una comparacion de verdad y no de
    # cadenas, donde "10" queda por debajo de "6".
    value_number: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    id_material_attribute_option: Mapped[int | None] = mapped_column(
        ForeignKey("material_attribute_option.id_material_attribute_option"),
        nullable=True,
    )

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
            "id_nm_material_attribute": self.id_nm_material_attribute,
            "id_material": self.id_material,
            "id_material_attribute": self.id_material_attribute,
            "value_text": self.value_text,
            "value_number": (
                float(self.value_number) if self.value_number is not None else None
            ),
            "id_material_attribute_option": self.id_material_attribute_option,
            "deletion_date": self.deletion_date.isoformat() if self.deletion_date else None,
        }
