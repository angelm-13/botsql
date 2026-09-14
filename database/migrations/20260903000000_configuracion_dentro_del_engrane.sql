-- Todo lo de Configuracion vive en el engrane, no repartido en tres sitios.
--
-- Que habia
-- ---------
-- 20260901180000 ya habia unificado Seguridad y Configuracion bajo un solo
-- encabezado "Configuracion" -pero adentro del menu vertical-, y el Gestor de
-- roles y permisos y Perfiles seguian aparte, fijos en la barra superior, sin
-- pasar por el gestor de roles en absoluto (location: "topbar" esta escrito a
-- mano en el frontend, no en la base). El resultado: para configurar algo
-- habia que acordarse de si estaba en el menu lateral o en la barra de arriba.
--
-- Que hace esta migracion
-- ------------------------
-- Mueve al engrane (menu_location = 'settings') cualquier fila que hoy este
-- agrupada bajo "Configuracion" en el menu vertical -Usuarios, Perfiles,
-- Departamentos, Subdepartamentos, Niveles, Registro de eventos, lo que sea
-- que el rol tenga concedido de ese grupo-. La parte de "Gestor de roles y
-- permisos" y "MFA de usuario" no tiene fila en `entity_permission` -son rutas
-- fijas del frontend, no entidades- asi que su cambio de ubicacion va en
-- Shell.jsx, junto con este commit.
--
-- Por que un UPDATE por grupo y no por entidad
-- ----------------------------------------------
-- Nombrar cada entidad a mano (`entity_name IN (...)`) se desactualiza en
-- cuanto alguien agregue una pantalla nueva a Configuracion: quedaria en el
-- menu vertical por descuido, exactamente el problema que se esta corrigiendo.
-- Filtrar por `menu_group = 'Configuracion'` alcanza a cualquier fila presente
-- o futura que caiga en ese grupo, sin mantenimiento aparte.
--
-- Reaplicable: solo toca filas que sigan en 'sidebar'. Una fila que ya se movio
-- -o que alguien devolvio al menu vertical a mano desde el gestor- no se pisa
-- en la siguiente corrida.

BEGIN;

UPDATE entity_permission
   SET menu_location = 'settings',
       last_update_date = now()
 WHERE deletion_date IS NULL
   AND menu_group = 'Configuracion'
   AND menu_location = 'sidebar';

COMMIT;
