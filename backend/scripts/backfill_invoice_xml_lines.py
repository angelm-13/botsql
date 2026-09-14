from __future__ import annotations

from app.models import Invoice, InvoiceMaterialService
from app.models.session import transaction_context
from app.services.cfdi_xml import parse_cfdi
from app.services.invoice_artifacts import invoice_xml_path
from app.services.invoice_xml_lines import persist_xml_lines


def invoices_without_lines() -> list[dict]:
    with transaction_context() as session:
        invoices = (
            session.query(Invoice)
            .outerjoin(
                InvoiceMaterialService,
                (InvoiceMaterialService.id_invoice == Invoice.id_invoice)
                & (InvoiceMaterialService.deletion_date.is_(None)),
            )
            .filter(Invoice.folio_fiscal.is_not(None))
            .filter(InvoiceMaterialService.id_invoice_material_service.is_(None))
            .order_by(Invoice.id_invoice)
            .all()
        )
        return [invoice.serialize() for invoice in invoices]


def main() -> int:
    created = 0
    skipped = 0
    errors = []
    for invoice in invoices_without_lines():
        path = invoice_xml_path(invoice['id_invoice'])
        if not path.is_file():
            skipped += 1
            continue
        try:
            concepts = parse_cfdi(path.read_bytes()).get('conceptos', [])
            if not concepts:
                skipped += 1
                continue
            lines = persist_xml_lines(invoice, concepts, user_id=invoice.get('created_by'))
            created += len(lines)
        except Exception as exc:
            errors.append(f"Factura {invoice['id_invoice']}: {exc}")

    print(f'Partidas creadas: {created}')
    print(f'Facturas omitidas: {skipped}')
    for error in errors:
        print(error)
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
