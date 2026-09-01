from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, BigInteger, SmallInteger, Boolean, Date, DateTime, Float, Numeric, ForeignKey, Text, JSON, Enum, LargeBinary, UniqueConstraint, func
from app.models.base import Base


def to_json_value(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.hex()
    return value


class Location(Base):
    __tablename__ = 'location'

    id_location: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    id_location_type: Mapped[int] = mapped_column(Integer, ForeignKey('location_type.id_location_type'), nullable=False)
    location_description: Mapped[object] = mapped_column(String(200), nullable=False)
    # Proyecto al que pertenece esta ubicacion, o nulo si es comun. El almacen
    # de cada proyecto es una rama del mismo arbol y no un almacen aparte, de
    # modo que "cuanto hay en total" y "cuanto hay del restaurante" se contestan
    # con la misma consulta y un filtro.
    id_module: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # Padre en la jerarquia almacen -> zona -> rack -> posicion. Era un
    # entero suelto, asi que admitia apuntar a una ubicacion inexistente.
    id_location_reference: Mapped[int] = mapped_column(Integer, ForeignKey('location.id_location'), nullable=True)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)

    def serialize(self) -> dict:
        return {
            'id_location': to_json_value(self.id_location),
            'id_location_type': to_json_value(self.id_location_type),
            'location_description': to_json_value(self.location_description),
            'id_location_reference': to_json_value(self.id_location_reference),
            'created_by': to_json_value(self.created_by),
            'creation_date': to_json_value(self.creation_date),
            'last_update_date': to_json_value(self.last_update_date),
            'deletion_date': to_json_value(self.deletion_date),
        }

    def serialize_summary(self) -> dict:
        return {'id_location': self.id_location}
