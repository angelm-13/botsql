BEGIN;

-- Folio de un sistema de cotizacion EXTERNO (ej. adser, obligado por su
-- proveedor a cotizar fuera de tyakxa_tny). `id_quotation` se queda como FK
-- real a `invoice` para cuando la cotizacion SI vive aqui; esta columna es
-- solo texto libre para cuando no existe ninguna fila de `invoice` que
-- represente ese folio. Las dos nunca se llenan a la vez.
ALTER TABLE proyect ADD COLUMN IF NOT EXISTS quotation_reference VARCHAR(80);

COMMIT;
