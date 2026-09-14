BEGIN;

-- De que renglon original viene esta partida, cuando el renglon es de una
-- nota de credito que acredita una cantidad puntual de un producto/servicio
-- ya facturado. Nulo para lo que no corresponde a un renglon original -una
-- bonificacion global, por ejemplo-. Ver invoice_credit_note_service.py.
ALTER TABLE invoice_material_service
    ADD COLUMN IF NOT EXISTS id_original_line INTEGER
        REFERENCES invoice_material_service (id_invoice_material_service);

CREATE INDEX IF NOT EXISTS ix_invoice_material_service_id_original_line
    ON invoice_material_service (id_original_line);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'ck_invoice_material_service_original_line_not_self'
    ) THEN
        ALTER TABLE invoice_material_service
            ADD CONSTRAINT ck_invoice_material_service_original_line_not_self
            CHECK (id_original_line IS NULL OR id_original_line <> id_invoice_material_service);
    END IF;
END $$;

COMMIT;
