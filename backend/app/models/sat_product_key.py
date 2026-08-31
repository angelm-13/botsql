"""Catalogo c_ClaveProdServ del SAT (clave de producto o servicio para CFDI 4.0).

El SAT exige que cada concepto lleve una ClaveProdServ de su catalogo oficial,
que ronda las 52,000 entradas. Sin la tabla, la captura obliga a teclear de
memoria una clave de 8 digitos y cualquier error se descubre hasta el timbrado.
Aqui se guarda el catalogo completo, sin filtrar por giro, y se llena desde el
archivo que publica el SAT con `scripts/import_sat_catalog.py`.
"""

from __future__ import annotations

import unicodedata
from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def normalize_search_text(value) -> str:
    """Pasa a minusculas y quita acentos, solo para buscar.

    En espanol se teclea "consultoria" y el catalogo dice "consultoria" con
    acento; sin normalizar, el LIKE no encuentra nada.
    """
    if not value:
        return ""
    decomposed = unicodedata.normalize("NFKD", str(value).lower())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


class SatProductKey(Base):
    """Una entrada del catalogo c_ClaveProdServ."""

    __tablename__ = "sat_product_key"
    __table_args__ = (
        Index("ix_sat_product_key_description_norm", "description_norm"),
        Index("ix_sat_product_key_keywords_norm", "keywords_norm"),
    )

    id_sat_product_key: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # Clave de 8 digitos, p. ej. '01010101'.
    clave: Mapped[str] = mapped_column(String(8), nullable=False, unique=True, index=True)
    # Descripcion oficial del SAT: es el texto que se muestra al capturar.
    description: Mapped[str] = mapped_column(Text, nullable=False)
    # "Palabras similares" que publica el SAT. Mejoran el acierto cuando el
    # nombre comercial no coincide con la descripcion oficial.
    keywords: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Copias normalizadas, solo para la busqueda. No se muestran.
    description_norm: Mapped[str | None] = mapped_column(Text, nullable=True)
    keywords_norm: Mapped[str | None] = mapped_column(Text, nullable=True)
    creation_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    def serialize(self) -> dict:
        return {
            "clave": self.clave,
            "description": self.description,
            "keywords": self.keywords or "",
        }
