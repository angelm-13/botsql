-- Foto de una incidencia, en base64.
--
-- La manda el flujo de n8n cuando alguien checa asistencia por WhatsApp: n8n
-- descifra la imagen y la entrega como cadena base64, que aqui se guarda tal
-- cual para poder mostrarla en la pantalla de Incidencias.
--
-- TEXT y no VARCHAR(n): una foto de telefono en base64 ocupa de cientos de KB a
-- varios MB y Postgres no pone tope a TEXT (hasta ~1 GB por valor; lo que pasa
-- de ~2 KB se guarda aparte, en TOAST, sin afectar al resto de la fila). El tope
-- real lo pone la validacion de la API (ver IncidentService._validate_foto) y el
-- limite de cuerpo del ingress (12m).
--
-- Opcional: solo las incidencias que traen foto la llenan. Solo columna nueva e
-- IF NOT EXISTS: la migracion se reaplica en cada arranque del pod y no toca
-- entity_permission ni ninguna columna scope_*. El permiso por campo lo deriva
-- el sembrado de nm_field_permission a partir de `field`, que se llena solo
-- desde el modelo.
BEGIN;

ALTER TABLE incident
    ADD COLUMN IF NOT EXISTS photo_base64 TEXT;

COMMIT;
