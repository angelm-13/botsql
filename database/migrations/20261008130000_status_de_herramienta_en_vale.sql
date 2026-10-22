-- `nm_incident_product.status`: el modelo (backend/app/models/nm_incident_product.py)
-- ya declaraba esta columna desde el commit 696b123, pero nunca se escribio la
-- migracion -- cualquier INSERT tronaba con
-- "column status of relation nm_incident_product does not exist".
--
-- Idempotente: ADD COLUMN IF NOT EXISTS.
BEGIN;

ALTER TABLE nm_incident_product
    ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'disponible';

COMMIT;
