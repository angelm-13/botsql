from __future__ import annotations

from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class InvoiceCfdiXml(Base):
    """XML timbrado de una factura: el comprobante fiscal en si.

    El PDF es solo su representacion grafica. El QR, la cadena original, el
    sello del emisor y el RFC del proveedor de certificacion se leen de este
    XML (`parse_cfdi`), asi que si se pierde, el PDF sale incompleto. Vivia solo
    como archivo en `/uploads/cfdi_xml`, que se borra con el pod si el volumen
    no esta montado. Aqui viaja con el respaldo de Postgres; el archivo queda
    como copia secundaria.

    Una fila por factura. Es una tabla aparte y no una columna de `invoice`
    para no arrastrar el texto del XML en cada consulta de facturas.
    """

    __tablename__ = "invoice_cfdi_xml"

    id_invoice: Mapped[int] = mapped_column(Integer, ForeignKey("invoice.id_invoice"), primary_key=True, autoincrement=False, nullable=False)
    xml: Mapped[str] = mapped_column(Text, nullable=False)
    creation_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_update_date: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
