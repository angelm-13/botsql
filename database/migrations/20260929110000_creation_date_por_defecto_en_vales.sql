-- `creation_date` de la incidencia y de su renglon de vale, con valor por defecto.
--
-- `init.sql` crea las dos columnas como `TIMESTAMP NULL` sin ningun DEFAULT,
-- mientras el modelo ORM las declara `NOT NULL DEFAULT now()`. El CRUD generico
-- no lo nota porque `_fill_system_defaults()` las rellena en Python, pero
-- `warehouse_voucher_service` inserta por su cuenta: ningun vale de almacen,
-- tampoco uno capturado hoy, guardaba cuando se capturo. Ver
-- docs/2026-09-28_creation_date_sin_default_en_incident.md.
--
-- Esta migracion arregla las altas FUTURAS de cualquier camino, sin depender de
-- que cada servicio se acuerde de rellenarla. Las filas que ya existen las
-- rellena `backend/scripts/fix_adser_creation_date.py`, no esta migracion:
-- necesita datos del sistema anterior que la base ya no tiene.
--
-- Idempotente: SET DEFAULT se puede repetir sin efecto, y no toca ninguna fila.
-- (Las migraciones corren completas en cada arranque del backend.)

ALTER TABLE incident ALTER COLUMN creation_date SET DEFAULT now();
ALTER TABLE nm_incident_product ALTER COLUMN creation_date SET DEFAULT now();
