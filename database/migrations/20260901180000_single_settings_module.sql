-- Un solo apartado de Configuracion.
--
-- Que habia
-- ---------
-- La configuracion estaba repartida en cuatro sitios: el grupo "Configuracion"
-- del menu (departamentos, subdepartamentos, niveles), el grupo "Seguridad"
-- (usuarios y perfiles), un menu de engrane en el encabezado y un renglon suelto
-- de "Configurar MFA" clavado arriba del menu. Encontrar una opcion era acordarse
-- de cual de los cuatro la tenia.
--
-- Que queda
-- ---------
-- Un grupo "Configuracion" con todo dentro. Seguridad sigue siendo un modulo
-- aparte para conceder acceso -si se fusionara, cualquier rol con configuracion
-- heredaria usuarios y permisos, y casi todos los roles la tienen porque
-- necesitan leer catalogos-; lo que se unifica es donde se ve, no quien entra.
--
-- El engrane
-- ----------
-- Lo sostenia una sola entrada, la conexion al dispositivo Kronos, que es el
-- reloj checador: pertenece a Recursos humanos. Se manda ahi y el engrane se
-- retira. Esta migracion arrastra cualquier fila que siguiera apuntando al
-- engrane, porque con el retirado esa entrada no tendria ninguna puerta y
-- desapareceria sin que nadie se entere.

BEGIN;

UPDATE entity_permission
   SET menu_location = 'sidebar',
       menu_group = COALESCE(NULLIF(menu_group, ''), 'Recursos humanos'),
       menu_group_icon = COALESCE(NULLIF(menu_group_icon, ''), 'hr'),
       menu_label = COALESCE(NULLIF(menu_label, ''), 'Conexión al dispositivo'),
       last_update_date = now()
 WHERE deletion_date IS NULL
   AND menu_location = 'settings';

-- Seguridad se pinta dentro de Configuracion. Se cambia solo la presentacion:
-- `entity_name` y los bits de cada fila quedan intactos, asi que quien no tenia
-- acceso a usuarios sigue sin tenerlo.
UPDATE entity_permission
   SET menu_group = 'Configuracion',
       menu_group_icon = 'settings',
       last_update_date = now()
 WHERE deletion_date IS NULL
   AND menu_group = 'Seguridad';

COMMIT;
