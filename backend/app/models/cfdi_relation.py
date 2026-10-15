from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.utils.tiempo import a_iso_utc


class CfdiRelation(Base):
    """Un comprobante declara con cual otro se relaciona y como.

    Es el nodo `CfdiRelacionados` del CFDI. Vale para mas que las notas de
    credito -tambien lo usan la sustitucion al cancelar y la aplicacion de
    anticipos-, asi que se modela aparte en lugar de meterlo en la factura.

    `related_uuid` es la referencia que viaja en el XML, y es la que manda: el
    comprobante relacionado puede ser de otro emisor y no vivir en este
    sistema. `id_related_invoice` se llena solo cuando si esta aqui, para poder
    navegar entre ambos sin buscar por folio.
    """

    __tablename__ = "cfdi_relation"
    __table_args__ = (
        UniqueConstraint(
            "id_invoice", "relation_type", "related_uuid",
            name="uq_cfdi_relation_invoice_type_uuid",
        ),
        UniqueConstraint("idempotency_key", name="uq_cfdi_relation_idempotency_key"),
        Index("ix_cfdi_relation_related_uuid", "related_uuid"),
        Index("ix_cfdi_relation_related_invoice", "id_related_invoice"),
    )

    id_cfdi_relation: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # El comprobante que declara la relacion; en una nota de credito, la nota.
    id_invoice: Mapped[int] = mapped_column(ForeignKey("invoice.id_invoice"), nullable=False)
    # c_TipoRelacion
    relation_type: Mapped[str] = mapped_column(String(2), nullable=False)
    related_uuid: Mapped[str] = mapped_column(String(36), nullable=False)
    id_related_invoice: Mapped[int | None] = mapped_column(ForeignKey("invoice.id_invoice"), nullable=True)
    # Identifica la operacion que creo la relacion, para no emitir dos veces la
    # misma nota de credito si la llamada se repite.
    idempotency_key: Mapped[str | None] = mapped_column(String(100), nullable=True)

    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    def serialize(self):
        return {
            "id_cfdi_relation": self.id_cfdi_relation,
            "id_invoice": self.id_invoice,
            "relation_type": self.relation_type,
            "related_uuid": self.related_uuid,
            "id_related_invoice": self.id_related_invoice,
            "idempotency_key": self.idempotency_key,
            "created_by": self.created_by,
            "creation_date": a_iso_utc(self.creation_date),
        }
