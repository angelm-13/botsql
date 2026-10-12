"""Recupera del PAC el XML de facturas ya timbradas que quedaron sin XML.

El timbrado de Facturama responde con el `Id` pero no con el XML, y antes de
este arreglo el sistema no lo descargaba: la factura quedaba "timbrada" con
UUID pero sin XML (el PDF salia sin QR y la descarga pedia adjuntarlo a mano).

Para cada factura con `folio_fiscal` y sin fila en `invoice_cfdi_xml`, toma el
`facturama_id` de su ultima operacion `stamped`, descarga el XML, exige que su
UUID coincida con el de la factura y lo guarda junto con los datos fiscales.
Idempotente: no toca facturas que ya tienen XML.

    python -m scripts.recover_stamped_xml --dry-run
    python -m scripts.recover_stamped_xml
"""

from __future__ import annotations

import argparse
import sys

from sqlalchemy import select

from app.models import Invoice, InvoiceCfdiXml, StampingOperation
from app.models.session import transaction_context
from app.services.cfdi_validation import validate_cfdi_xml
from app.services.cfdi_xml import parse_cfdi
from app.services.cfdi_xml_store import save_cfdi_xml
from app.services.stamping import configured_provider


def run(dry_run: bool) -> dict:
    recuperadas, sin_id, errores, avisos = [], [], [], []
    provider = configured_provider()
    with transaction_context() as db:
        con_xml = {fila[0] for fila in db.query(InvoiceCfdiXml.id_invoice).all()}
        facturas = db.scalars(
            select(Invoice).where(Invoice.folio_fiscal.is_not(None)).order_by(Invoice.id_invoice)
        ).all()
        for factura in facturas:
            if factura.id_invoice in con_xml:
                continue
            operacion = db.scalars(
                select(StampingOperation)
                .where(StampingOperation.id_invoice == factura.id_invoice, StampingOperation.status == "stamped")
                .order_by(StampingOperation.id_stamping_operation.desc())
            ).first()
            facturama_id = (operacion.response_metadata or {}).get("facturama_id") if operacion else None
            if not facturama_id:
                sin_id.append(factura.id_invoice)
                continue
            xml = provider.download_xml(facturama_id)
            if not xml:
                errores.append(f"Factura {factura.id_invoice}: Facturama no devolvio el XML (id {facturama_id})")
                continue
            xml_bytes = xml.encode("utf-8")
            try:
                datos = parse_cfdi(xml_bytes)
            except Exception as exc:
                errores.append(f"Factura {factura.id_invoice}: XML ilegible: {exc}")
                continue
            uuid_xml = str(datos.get("uuid") or "").strip().upper()
            if uuid_xml != str(factura.folio_fiscal).strip().upper():
                errores.append(f"Factura {factura.id_invoice}: UUID del XML ({uuid_xml}) distinto al de la factura ({factura.folio_fiscal})")
                continue
            for problema in validate_cfdi_xml(xml_bytes):
                avisos.append(f"Factura {factura.id_invoice}: {problema}")
            save_cfdi_xml(db, factura.id_invoice, xml)
            factura.cfdi_code = datos["uuid"]
            factura.no_certificado = datos.get("no_certificado")
            factura.no_certificado_sat = datos.get("no_certificado_sat")
            factura.sello_sat = datos.get("sello_sat")
            recuperadas.append(factura.id_invoice)
        db.flush()
        if dry_run:
            db.rollback()
    return {"recuperadas": recuperadas, "sin_id": sin_id, "errores": errores, "avisos": avisos}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--dry-run", action="store_true", help="hace todo y deshace la transaccion")
    args = parser.parse_args(argv)
    r = run(args.dry_run)
    print(("[dry-run] " if args.dry_run else "") + f"XML recuperados: {len(r['recuperadas'])} {r['recuperadas']}")
    print(f"Sin facturama_id en su operacion (adjuntar a mano): {r['sin_id']}")
    for linea in r["avisos"] + r["errores"]:
        print(linea)
    return 1 if r["errores"] else 0


if __name__ == "__main__":
    sys.exit(main())
