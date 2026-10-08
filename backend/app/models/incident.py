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


class Incident(Base):
    __tablename__ = 'incident'

    id_incident: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    incident_date: Mapped[object] = mapped_column(DateTime, nullable=True)
    id_incident_type: Mapped[int] = mapped_column(Integer, ForeignKey('incident_type.id_incident_type'), nullable=False)
    note: Mapped[object] = mapped_column(String(300), nullable=True)
    id_user: Mapped[int] = mapped_column(Integer, ForeignKey('user.id_user'), nullable=False)
    incident_status: Mapped[object] = mapped_column(String(20), nullable=True)
    close_date: Mapped[object] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deletion_date: Mapped[object] = mapped_column(DateTime, nullable=True)
    # El proyecto al que pertenece, cuando pertenece a alguno. Nulo en un vale
    # de almacen, que tambien es un `incident` y no es de ningun proyecto.
    id_proyect: Mapped[int] = mapped_column(Integer, ForeignKey('proyect.id_proyect'), nullable=True)
    id_lider: Mapped[int] = mapped_column(Integer, nullable=True)
    # El numero con el que la gente conoce este vale. En el sistema anterior era
    # `incidente.id_incidente` -su propia llave-, asi que no se puede reusar la
    # nuestra: `id_incident` tiene su secuencia y la tabla ya trae filas.
    external_folio: Mapped[str | None] = mapped_column(String(40), nullable=True)
    # De donde vino. Un folio "140" no significa lo mismo en dos origenes.
    external_source: Mapped[str | None] = mapped_column(String(30), nullable=True)
    # Vale complementario: el vale anterior, del mismo proyecto, al que este
    # agrega herramienta. Solo trazabilidad.
    id_incident_parent: Mapped[int | None] = mapped_column(
        Integer, ForeignKey('incident.id_incident'), nullable=True)
    # Quien recoge cuando no tiene usuario (externo). Excluyente con
    # `nm_incident_product.id_user_delivered_to`.
    pickup_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # true solo en los vales nuevos: de ellos se espera entrega y confirmacion.
    # Los anteriores quedan en false ("sin seguimiento"), sin confirmaciones
    # inventadas.
    tracks_delivery: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default='false')
    # Almacen marca "entregado a X", acto aparte de autorizar.
    delivered_date: Mapped[object] = mapped_column(DateTime, nullable=True)
    delivered_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    delivered_to_user: Mapped[int | None] = mapped_column(Integer, nullable=True)
    delivered_to_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    delivery_note: Mapped[str | None] = mapped_column(String(300), nullable=True)
    # El supervisor responsable confirma el recibido (con o sin observaciones).
    received_confirmed_date: Mapped[object] = mapped_column(DateTime, nullable=True)
    received_confirmed_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    receipt_ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    receipt_note: Mapped[str | None] = mapped_column(String(300), nullable=True)

    def serialize(self) -> dict:
        return {
            'id_incident': to_json_value(self.id_incident),
            'incident_date': to_json_value(self.incident_date),
            'id_incident_type': to_json_value(self.id_incident_type),
            'note': to_json_value(self.note),
            'id_user': to_json_value(self.id_user),
            'incident_status': to_json_value(self.incident_status),
            'close_date': to_json_value(self.close_date),
            'created_by': to_json_value(self.created_by),
            'creation_date': to_json_value(self.creation_date),
            'last_update_date': to_json_value(self.last_update_date),
            'deletion_date': to_json_value(self.deletion_date),
            'id_proyect': to_json_value(self.id_proyect),
            'id_lider': to_json_value(self.id_lider),
            'external_folio': to_json_value(self.external_folio),
            'external_source': to_json_value(self.external_source),
            'id_incident_parent': to_json_value(self.id_incident_parent),
            'pickup_name': to_json_value(self.pickup_name),
            'tracks_delivery': bool(self.tracks_delivery),
            'delivered_date': to_json_value(self.delivered_date),
            'delivered_by': to_json_value(self.delivered_by),
            'delivered_to_user': to_json_value(self.delivered_to_user),
            'delivered_to_name': to_json_value(self.delivered_to_name),
            'delivery_note': to_json_value(self.delivery_note),
            'received_confirmed_date': to_json_value(self.received_confirmed_date),
            'received_confirmed_by': to_json_value(self.received_confirmed_by),
            'receipt_ok': to_json_value(self.receipt_ok),
            'receipt_note': to_json_value(self.receipt_note),
        }

    def serialize_summary(self) -> dict:
        return {'id_incident': self.id_incident}
