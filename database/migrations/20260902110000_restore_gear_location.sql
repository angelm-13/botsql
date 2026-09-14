-- Devolver el engrane del encabezado como ubicacion de menu.
--
-- Que se rompio
-- -------------
-- La migracion 20260901180000 movio al menu vertical todas las filas con
-- `menu_location = 'settings'`, razonando que habia demasiados sitios donde
-- configurar cosas y que el engrane era uno de mas.
--
-- Era un error de lectura. El engrane no es un cajon de sastre: es una de las
-- tres UBICACIONES que el gestor de roles ofrece por rol y por entidad -Menu
-- vertical, Engrane, No mostrar-. Moverlo todo al menu vertical no simplifico
-- nada; le quito al sistema una opcion de configuracion que alguien habia
-- elegido a proposito, y dejo la columna UBICACION del gestor ofreciendo un
-- destino que ya no existia.
--
-- Que hace esta migracion
-- -----------------------
-- Devuelve al engrane la conexion al dispositivo Kronos, que es la entrada que
-- vivia ahi y la que el registro declara como `menu="settings"`. No intenta
-- adivinar otras: 20260901180000 no guardo que fila venia de donde, asi que
-- cualquier otra que se hubiera asignado al engrane a mano hay que volver a
-- ponerla desde el gestor. Se dice en vez de fingir que se restauro todo.
--
-- Lo que NO se toca son las filas que 20260901180000 movio de `Seguridad` al
-- grupo `Configuracion`: eso sigue siendo lo que se quiso -un solo apartado de
-- configuracion en el menu vertical- y no tiene nada que ver con el engrane.

BEGIN;

UPDATE entity_permission
   SET menu_location = 'settings',
       last_update_date = now()
 WHERE deletion_date IS NULL
   AND entity_name = 'kronos_device'
   AND menu_location = 'sidebar';

COMMIT;
