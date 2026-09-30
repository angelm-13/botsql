-- La bitacora diaria de taller ya tenia pantalla propia (`activity_logs`) y
-- capacidad concedida a Jefe de taller (ver
-- 20260928100000_resembrar_catalogo_bitacora_jefe_de_taller.sql), pero se
-- sembro con `menu="hidden"` -- Jefe de taller no tenia ninguna entrada de
-- menu para llegar a ella, aunque el permiso ya estuviera concedido.
--
-- El generador (`seed_module_permissions.py`) no REPONE el menu de una fila
-- de `entity_permission` que ya existe -- solo entra a rellenar filas
-- nuevas o a corregir el rol equivocado (ver el DELETE+INSERT de la
-- migracion que resiembra la matriz completa) -- asi que subir el registro
-- a `menu="sidebar"` no alcanza solo: hace falta este UPDATE para las
-- instalaciones que ya sembraron la fila con el menu viejo.
--
-- Se reaplica en cada arranque del pod: el WHERE es por entity_name, sin
-- IDs fijos, y no hace nada la segunda vez que el menu ya este correcto.
BEGIN;

UPDATE entity_permission
   SET menu_location = 'sidebar',
       menu_group = 'Operaciones',
       menu_group_icon = 'operations',
       menu_label = 'Bitacora diaria de taller',
       menu_order = 390
 WHERE entity_name = 'daily_activity_log'
   AND (menu_location IS DISTINCT FROM 'sidebar'
        OR menu_label IS DISTINCT FROM 'Bitacora diaria de taller');

COMMIT;
