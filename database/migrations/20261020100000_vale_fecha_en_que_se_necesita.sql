-- La fecha para la que se necesita la herramienta de un vale (2026-10-20).
--
-- El vale pedia "Debe volver el", y el prestamo no tiene fecha fija de regreso: lo
-- que quien pide SI sabe es para cuando necesita la herramienta. Esa fecha es del
-- vale completo, no de un renglon, y es solo informativa -no marca vencidos-.
--
-- Idempotente: toda migracion se reaplica en cada arranque.
ALTER TABLE incident ADD COLUMN IF NOT EXISTS needed_date date;
