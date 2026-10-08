"""Guarda y lee el XML timbrado de una factura: la base manda, el archivo respalda.

Una sola fuente para quien necesite el XML (PDF, descarga, validaciones). El
orden de lectura es la base primero y el archivo en `/uploads/cfdi_xml` despues,
porque el archivo se pierde si el volumen no esta montado y la base no.
"""

from __future__ import annotations

from app.models.invoice_cfdi_xml import InvoiceCfdiXml
from app.models.session import transaction_context
from app.services.invoice_artifacts import invoice_xml_path, save_invoice_xml


def _como_texto(xml_content) -> str:
    if isinstance(xml_content, str):
        return xml_content
    return bytes(xml_content).decode("utf-8")


def _xml_en_base(db, id_invoice: int) -> str | None:
    fila = db.get(InvoiceCfdiXml, id_invoice)
    return fila.xml if fila is not None else None


def save_cfdi_xml(db, id_invoice, xml_content, upload_root=None) -> None:
    """Guarda el XML en la base (dentro de la transaccion `db`) y en disco.

    La base va dentro de la transaccion del llamador: si el timbrado se revierte,
    el XML tambien. El archivo es mejor esfuerzo; que falle la copia no debe
    tumbar un comprobante que ya quedo en la base.
    """
    texto = _como_texto(xml_content)
    fila = db.get(InvoiceCfdiXml, int(id_invoice))
    if fila is None:
        db.add(InvoiceCfdiXml(id_invoice=int(id_invoice), xml=texto))
    else:
        fila.xml = texto
    db.flush()
    try:
        save_invoice_xml(id_invoice, texto, upload_root)
    except OSError:
        pass


def load_cfdi_xml(id_invoice, upload_root=None, db=None) -> bytes | None:
    """XML de la factura: de la base si esta, si no del archivo, si no `None`."""
    if not id_invoice:
        return None
    try:
        id_int = int(id_invoice)
    except (TypeError, ValueError):
        return None
    if db is not None:
        texto = _xml_en_base(db, id_int)
    else:
        with transaction_context() as sesion:
            texto = _xml_en_base(sesion, id_int)
    if texto:
        return texto.encode("utf-8")
    ruta = invoice_xml_path(id_int, upload_root)
    return ruta.read_bytes() if ruta.is_file() else None
