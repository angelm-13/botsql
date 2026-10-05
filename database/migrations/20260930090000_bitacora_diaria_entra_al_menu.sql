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
-- Se reaplica en cada arranque del pod (db-migrate corre TODAS las migraciones
-- cada vez), asi que solo toca una fila que sigue EXACTAMENTE como la dejo la
-- siembra original: oculta (`menu_location = 'hidden'`) y sin grupo ni etiqueta.
-- El WHERE es por entity_name, sin IDs fijos.
--
-- Corregido 2026-09-30: la condicion anterior era `menu_location IS DISTINCT
-- FROM 'sidebar' OR menu_label IS DISTINCT FROM '...'`, que compara contra el
-- valor DESEADO y no contra el de la siembra. Con eso, un administrador que
-- ocultaba la pantalla ("No mostrar") o la movia al engrane desde el Gestor de
-- roles veia su decision revertida en el siguiente reinicio del backend. Ahora,
-- despues de aplicarse una vez la fila ya tiene grupo y etiqueta (el Gestor los
-- conserva al guardar), asi que no vuelve a coincidir y lo que el administrador
-- decida perdura -- el Gestor manda.
--
-- Corregido 2026-10-05, por la migracion
-- `20260816000000_el_gestor_manda_sobre_las_migraciones.sql` (fecha de archivo
-- anterior a esta, asi que corre primero): esa migracion congela TODO
-- `entity_permission` (pone `ajustado_por_gestor`) la primera vez que corre en
-- una base ya en uso -- torredigital-prod y adser-prod, que todavia no tienen
-- este UPDATE aplicado. Sin fijar tambien `ajustado_por_gestor` aqui, el
-- trigger `trg_gestor_manda` descartaria este UPDATE en esos dos ambientes (la
-- fila ya frozen, este UPDATE no toca esa columna) y la bitacora de taller se
-- quedaria oculta ahi para siempre, en silencio, sin error. En tyakxa-dev no
-- cambia nada: la fila ya tiene el menu correcto desde antes.
BEGIN;

UPDATE entity_permission
   SET menu_location = 'sidebar',
       menu_group = 'Operaciones',
       menu_group_icon = 'operations',
       menu_label = 'Bitacora diaria de taller',
       menu_order = 390,
       ajustado_por_gestor = now()
 WHERE entity_name = 'daily_activity_log'
   AND menu_location = 'hidden'
   AND COALESCE(menu_group, '') = ''
   AND COALESCE(menu_label, '') = '';

COMMIT;
