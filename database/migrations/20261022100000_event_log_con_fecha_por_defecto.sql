-- `creation_date` y `last_update_date` del registro de eventos, con valor por defecto.
--
-- El modelo ORM (`EventLog`) las declara `server_default=now()`, pero la tabla
-- salio de `init.sql` sin ningun DEFAULT. El CRUD generico las rellena en Python,
-- pero `audit_event` inserta sin ellas: los 39 asientos de vales (`incident` /
-- `transition`) y 2 de baja de usuario quedaron sin fecha -se sabe quien y que,
-- no cuando-. Mismo patron que `incident.creation_date` (20260929110000).
--
-- Arregla los asientos FUTUROS de cualquier camino. Los que ya existen se quedan
-- sin fecha a proposito: la base no tiene de donde sacarla y inventarla falsearia
-- la bitacora.
--
-- Idempotente: SET DEFAULT se puede repetir sin efecto y no toca ninguna fila.
-- (Las migraciones corren completas en cada arranque del backend.)

ALTER TABLE event_log ALTER COLUMN creation_date SET DEFAULT now();
ALTER TABLE event_log ALTER COLUMN last_update_date SET DEFAULT now();
