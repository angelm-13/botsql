ALTER TABLE customer_supplier
    ADD COLUMN IF NOT EXISTS is_principal BOOLEAN NOT NULL DEFAULT FALSE;

CREATE UNIQUE INDEX IF NOT EXISTS uq_customer_supplier_single_principal
    ON customer_supplier (is_principal)
    WHERE is_principal = TRUE AND deletion_date IS NULL;

ALTER TABLE invoice
    ADD COLUMN IF NOT EXISTS invoice_direction VARCHAR(20);

ALTER TABLE invoice
    DROP CONSTRAINT IF EXISTS ck_invoice_direction;

ALTER TABLE invoice
    ADD CONSTRAINT ck_invoice_direction
    CHECK (invoice_direction IN ('venta', 'compra', 'sin_clasificar'));