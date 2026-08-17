BEGIN;

ALTER TABLE invoice_material_service
    ADD COLUMN IF NOT EXISTS id_task INTEGER REFERENCES task(id_task);

CREATE INDEX IF NOT EXISTS ix_invoice_material_service_id_task
    ON invoice_material_service (id_task);

COMMIT;