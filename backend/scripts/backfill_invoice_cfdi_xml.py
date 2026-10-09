"""Carga a la tabla `invoice_cfdi_xml` los XML que hoy solo existen como archivo.

Para cada factura con archivo `cfdi_xml/invoice_<id>.xml` y sin fila en la tabla,
inserta el XML. Idempotente: no toca filas que ya existen ni facturas sin
archivo. Valida cada XML con `parse_cfdi` y exige que su UUID coincida con el
`folio_fiscal` de la factura, para no colgar el XML de otro comprobante.

    python -m scripts.backfill_invoice_cfdi_xml --dry-run
    python -m scripts.backfill_invoice_cfdi_xml

Con `--dry-run` hace todo y deshace la transaccion al final.
"""

from __future__ import annotations

import argparse
import sys

from app.models import Invoice, InvoiceCfdiXml
from app.models.session import transaction_context
from app.services.cfdi_xml import parse_cfdi
from app.services.invoice_artifacts import invoice_xml_path


def run(dry_run: bool) -> dict:
    cargadas, ya_estaban, sin_archivo, errores = [], [], [], []
    with transaction_context() as db:
        existentes = {fila[0] for fila in db.query(InvoiceCfdiXml.id_invoice).all()}
        facturas = db.query(Invoice).order_by(Invoice.id_invoice).all()
        for factura in facturas:
            id_factura = factura.id_invoice
            if id_factura in existentes:
                ya_estaban.append(id_factura)
                continue
            ruta = invoice_xml_path(id_factura)
            if not ruta.is_file():
                if factura.folio_fiscal:
                    sin_archivo.append(id_factura)
                continue
            contenido = ruta.read_bytes()
            try:
                uuid_xml = str(parse_cfdi(contenido).get("uuid") or "").strip().upper()
                texto = contenido.decode("utf-8")
            except Exception as exc:  # XML ilegible: se reporta, no se carga
                errores.append(f"Factura {id_factura}: {exc}")
                continue
            uuid_factura = str(factura.folio_fiscal or "").strip().upper()
            if uuid_factura and uuid_xml != uuid_factura:
                errores.append(f"Factura {id_factura}: el UUID del XML ({uuid_xml}) no coincide con el de la factura ({uuid_factura})")
                continue
            db.add(InvoiceCfdiXml(id_invoice=id_factura, xml=texto))
            cargadas.append(id_factura)
        db.flush()
        if dry_run:
            db.rollback()
    return {"cargadas": cargadas, "ya_estaban": ya_estaban, "sin_archivo": sin_archivo, "errores": errores}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--dry-run", action="store_true", help="hace todo y deshace la transaccion")
    args = parser.parse_args(argv)
    resultado = run(args.dry_run)
    print(("[dry-run] " if args.dry_run else "") + f"XML cargados: {len(resultado['cargadas'])}")
    print(f"Ya estaban en la base: {len(resultado['ya_estaban'])}")
    print(f"Facturas timbradas SIN archivo ni fila (hay que re-adjuntar el XML): {len(resultado['sin_archivo'])}")
    for id_factura in resultado["sin_archivo"]:
        print(f"  - factura {id_factura}")
    for error in resultado["errores"]:
        print(error)
    return 1 if resultado["errores"] else 0


if __name__ == "__main__":
    sys.exit(main())
