-- Quien tenia la pieza cuando se reporta su destruccion o extravio.
--
-- Al registrar la baja de algo que estaba prestado, el prestamo se cierra; hasta
-- ahora no quedaba dicho a quien se le cerro. Va en el renglon del reporte y lo pone
-- el sistema desde los prestamos abiertos del producto: nadie lo escribe a mano.
-- Solo una columna nueva con IF NOT EXISTS: la migracion se reaplica en cada
-- arranque del pod y no toca entity_permission ni ninguna columna scope_*.
BEGIN;

ALTER TABLE nm_incident_product
    ADD COLUMN IF NOT EXISTS held_by_user INTEGER REFERENCES "user" (id_user);

COMMIT;
