-- Vale de almacen: entrega separada de la autorizacion, confirmacion de recibido
-- por el supervisor, quien recoge sin usuario (externo) y vale complementario.
--
-- Todo es aditivo y nulo por omision: un vale anterior (incluidos los ~139 que se
-- migraron de Adser) queda con `tracks_delivery = false`, es decir "sin
-- seguimiento de entrega". NO se rellena ninguna confirmacion: seria inventar
-- que alguien recibio algo que nadie confirmo.
--
-- Se reaplica en cada arranque del pod (sin tabla de control, ver
-- ARQUITECTURA_TYAKXA_TNY.md 7.1): todo es `ADD COLUMN IF NOT EXISTS`. No toca
-- ninguna columna `scope_*` de `entity_permission`.
BEGIN;

ALTER TABLE incident
    -- "Complementario de": el vale anterior, del mismo proyecto, al que este
    -- agrega herramienta. Solo trazabilidad: no cambia permisos ni inventario.
    ADD COLUMN IF NOT EXISTS id_incident_parent INTEGER REFERENCES incident (id_incident),
    -- Quien recoge cuando NO tiene usuario en el sistema (chofer, mensajero).
    -- Excluyente con el `id_user_pickup` que cada renglon ya guarda en
    -- `nm_incident_product.id_user_delivered_to`.
    ADD COLUMN IF NOT EXISTS pickup_name VARCHAR(120),
    -- true solo en los vales nuevos: de ellos se espera entrega y confirmacion.
    ADD COLUMN IF NOT EXISTS tracks_delivery BOOLEAN NOT NULL DEFAULT false,
    -- Almacen marca "entregado a X" (acto aparte de autorizar).
    ADD COLUMN IF NOT EXISTS delivered_date TIMESTAMP,
    ADD COLUMN IF NOT EXISTS delivered_by INTEGER,
    ADD COLUMN IF NOT EXISTS delivered_to_user INTEGER,
    ADD COLUMN IF NOT EXISTS delivered_to_name VARCHAR(120),
    ADD COLUMN IF NOT EXISTS delivery_note VARCHAR(300),
    -- El supervisor responsable confirma que lo recibio (ok) o que lo recibio
    -- con observaciones (receipt_ok = false + nota).
    ADD COLUMN IF NOT EXISTS received_confirmed_date TIMESTAMP,
    ADD COLUMN IF NOT EXISTS received_confirmed_by INTEGER,
    ADD COLUMN IF NOT EXISTS receipt_ok BOOLEAN,
    ADD COLUMN IF NOT EXISTS receipt_note VARCHAR(300);

ALTER TABLE nm_incident_product
    -- A quien se entrego la pieza cuando no es un usuario (externo).
    ADD COLUMN IF NOT EXISTS delivered_to_name VARCHAR(120);

COMMIT;
