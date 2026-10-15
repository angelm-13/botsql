from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
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


class InvoiceCancellation(Base):
    """Solicitud de cancelacion de un CFDI y su desenlace ante el SAT.

    Cancelar no es un interruptor: se solicita y el SAT responde. Cuando el
    receptor tiene que aceptar, la solicitud queda "en proceso" hasta 72 horas,
    y de ahi puede salir cancelada o rechazada. Guardar solo una bandera en la
    factura perderia ese intermedio, que es justo donde hay que saber que paso.

    Se conserva cada intento, no solo el ultimo: si una cancelacion se rechaza
    y se vuelve a solicitar con otro motivo, ambos quedan registrados.
    """

    __tablename__ = "invoice_cancellation"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_invoice_cancellation_idempotency_key"),
        Index("ix_invoice_cancellation_invoice", "id_invoice", "creation_date"),
        Index("ix_invoice_cancellation_status", "status"),
    )

    id_invoice_cancellation: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_invoice: Mapped[int] = mapped_column(ForeignKey("invoice.id_invoice"), nullable=False)
    id_proyect: Mapped[int] = mapped_column(ForeignKey("proyect.id_proyect"), nullable=False)

    # c_MotivoCancelacion: 01 con relacion, 02 sin relacion, 03 no se realizo
    # la operacion, 04 nominativa dentro de una factura global.
    motive: Mapped[str] = mapped_column(String(2), nullable=False)
    # Solo con motivo 01: el folio fiscal del comprobante que sustituye a este.
    substitution_uuid: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # solicitada -> en_proceso -> cancelado | rechazado
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    provider: Mapped[str] = mapped_column(String(30), nullable=False)
    provider_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Acuse de cancelacion que devuelve el SAT, que es el comprobante de que se
    # solicito y con que resultado.
    acknowledgement: Mapped[str | None] = mapped_column(String(64), nullable=True)
    response_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)

    reason: Mapped[str | None] = mapped_column(String(300), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False)

    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
    resolved_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def serialize(self):
        return {
            "id_invoice_cancellation": self.id_invoice_cancellation,
            "id_invoice": self.id_invoice,
            "id_proyect": self.id_proyect,
            "motive": self.motive,
            "substitution_uuid": self.substitution_uuid,
            "status": self.status,
            "provider": self.provider,
            "provider_reference": self.provider_reference,
            "acknowledgement": self.acknowledgement,
            "response_metadata": self.response_metadata,
            "error_code": self.error_code,
            "reason": self.reason,
            "idempotency_key": self.idempotency_key,
            "created_by": self.created_by,
            "creation_date": a_iso_utc(self.creation_date),
            "resolved_date": self.resolved_date.isoformat() if self.resolved_date else None,
        }
