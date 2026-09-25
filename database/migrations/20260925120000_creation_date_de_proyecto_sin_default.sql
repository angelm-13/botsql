BEGIN;

-- `proyect.creation_date` se creo en 20260817020100_init_schema.sql como
-- "TIMESTAMP NULL", sin DEFAULT -- a diferencia de casi todas las columnas
-- `creation_date` de tablas mas nuevas (ej. `proyect_event`,
-- `proyect_document`, `customer_contact`), que si traen
-- "DEFAULT CURRENT_TIMESTAMP" desde su propia migracion de alta.
-- `create_project` (backend/app/services/project_management_service.py)
-- nunca la manda a mano -- confia en que la base la llene sola -- asi que
-- CUALQUIER proyecto nuevo queda con `creation_date = NULL`. Confirmado en
-- los 4 ambientes reales (tyakxa-dev, torredigital-prod, adser-prod,
-- vidrioyaluminios-prod): la columna de "Creacion" en Gestion de proyectos
-- sale en blanco para todo proyecto creado desde que existe esta pantalla.
ALTER TABLE proyect ALTER COLUMN creation_date SET DEFAULT CURRENT_TIMESTAMP;

-- Repara los proyectos ya afectados. `last_update_date` NO sirve de
-- aproximacion -- es la fecha de la ULTIMA edicion, y en varios de estos
-- proyectos ya se separa de la fecha real de creacion por dias (confirmado
-- caso por caso). `proyect_event` si trae su propia `creation_date` desde
-- que existe (20260822190000_project_management.sql), y cada proyecto
-- afectado en los 4 ambientes tiene exactamente un evento 'created' -- cero
-- proyectos sin ese evento, cero con mas de uno -- asi que el MIN() es la
-- fecha real de creacion, no una aproximacion.
UPDATE proyect
SET creation_date = evento.primera_fecha
FROM (
    SELECT id_proyect, MIN(creation_date) AS primera_fecha
    FROM proyect_event
    WHERE event_type = 'created'
    GROUP BY id_proyect
) evento
WHERE proyect.id_proyect = evento.id_proyect
  AND proyect.creation_date IS NULL;

-- Respaldo para el caso (no encontrado hoy en ningun ambiente real, pero
-- posible en una instalacion nueva sembrada distinto) de un proyecto sin su
-- evento 'created': mejor la fecha de la ultima edicion que un hueco en
-- blanco.
UPDATE proyect
SET creation_date = COALESCE(last_update_date, CURRENT_TIMESTAMP)
WHERE creation_date IS NULL;

COMMIT;
