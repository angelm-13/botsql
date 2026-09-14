-- Configuracion vuelve al engrane, y esta vez se queda.
--
-- Que pasaba
-- ----------
-- La migracion 20260903000000 ya movio `menu_group='Configuracion'` de la barra
-- lateral al engrane, y se confirmo funcionando. Pero volvio a aparecer.
--
-- No fue una regresion del front. La causa estaba en la SIEMBRA: en
-- `registry.filas_de_permisos()` la ubicacion se decidia asi
--
--     "sidebar" if etiqueta else "hidden"
--
-- es decir, TODA entidad con etiqueta de menu iba a la barra, sin que el modulo
-- pudiera opinar. Asi que cada vez que alguien resembraba los permisos --
-- instalacion nueva, rol nuevo, cliente nuevo -- `department`, `subdepartment`
-- y `level` volvian a la barra con el grupo "Configuracion", y el apartado
-- reaparecia. Una migracion escrita a mano no podia ganarle a eso: arreglaba
-- las filas de ese momento y la siguiente siembra las deshacia.
--
-- El arreglo de verdad va en el registro -- el modulo declara `menu="settings"`
-- --, y esta migracion solo endereza las filas que ya quedaron torcidas.
--
-- Por que solo tres entidades
-- ---------------------------
-- Porque `status` y `theme`, las otras dos del modulo, no tienen etiqueta en
-- MENU y por tanto se sembraban como `hidden`. Solo se colaban las que se ven.

BEGIN;

UPDATE entity_permission
   SET menu_location = 'settings',
       last_update_date = CURRENT_TIMESTAMP
 WHERE menu_group = 'Configuracion'
   AND menu_location = 'sidebar'
   AND deletion_date IS NULL;

-- Lo mismo para Seguridad, que comparte el apartado visible con Configuracion
-- -- son dos modulos de permisos distintos a proposito, pero un solo grupo en
-- pantalla -- y llegaba a la barra por la misma linea de codigo.
UPDATE entity_permission
   SET menu_location = 'settings',
       last_update_date = CURRENT_TIMESTAMP
 WHERE menu_group = 'Seguridad'
   AND menu_location = 'sidebar'
   AND deletion_date IS NULL;

COMMIT;
