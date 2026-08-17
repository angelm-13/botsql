BEGIN;

CREATE UNIQUE INDEX IF NOT EXISTS uq_invoice_folio_fiscal
    ON invoice (folio_fiscal)
    WHERE folio_fiscal IS NOT NULL;

COMMIT;