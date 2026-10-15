-- Latitud, longitud y distancia de una incidencia.
--
-- Las llena el flujo de n8n cuando alguien checa asistencia por WhatsApp: hasta
-- ahora viajaban dentro de `note` como un JSON de texto, que no se podia
-- ordenar, filtrar ni mostrar en columnas. Son opcionales: solo las incidencias
-- tipo "checador" las traen.
--
--   latitude / longitude: donde estaba la persona al checar (grados decimales).
--   distance_m: distancia en metros entre esa posicion y el punto de checada.
--
-- Solo columnas nuevas e IF NOT EXISTS: la migracion se reaplica en cada
-- arranque del pod y no toca entity_permission ni ninguna columna scope_*.
-- Los permisos por campo de estas columnas los deriva el sembrado de
-- nm_field_permission a partir de `entity_permission` y de `field`.
BEGIN;

ALTER TABLE incident
    ADD COLUMN IF NOT EXISTS latitude NUMERIC(10, 7),
    ADD COLUMN IF NOT EXISTS longitude NUMERIC(10, 7),
    ADD COLUMN IF NOT EXISTS distance_m NUMERIC(10, 2);

COMMIT;
