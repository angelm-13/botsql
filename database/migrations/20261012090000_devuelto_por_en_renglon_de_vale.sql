-- Quien devuelve la herramienta cuando no es el responsable del vale.
--
-- El vale puede salir y ser recogido por otra persona (un operador, un
-- externo); al cerrarlo, "Marcar devuelto" deja constancia de quien la trajo.
-- Va en el renglon de ENTRADA, que es el hecho de que volvio. Solo columnas
-- nuevas e IF NOT EXISTS: la migracion se reaplica en cada arranque del pod
-- y no toca entity_permission ni ninguna columna scope_*.
BEGIN;

ALTER TABLE nm_incident_product
    ADD COLUMN IF NOT EXISTS returned_by_user INTEGER REFERENCES "user" (id_user),
    ADD COLUMN IF NOT EXISTS returned_by_name VARCHAR(120);

COMMIT;
