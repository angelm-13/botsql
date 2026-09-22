-- Cinco roles que no concedian nada propio.
--
-- Que se retira y por que
-- -----------------------
-- `Jefe de taller` concedia EXACTAMENTE lo mismo que Supervisor: operaciones
-- en CAPTURA, inventario en CONSULTA, configuracion en CONSULTA -- 28 filas de
-- permiso identicas, medidas en la base. Se distinguia en una sola capacidad,
-- `project_execution`. Mantener un rol entero en paralelo para eso es
-- garantizar que los dos se desincronicen en cuanto alguien toque uno y no el
-- otro, que es lo que ya habia pasado: en la base, Jefe de taller tenia
-- `proyect` en 6 y `task_type` en 2 donde el registro dice 7 para ambos.
--
-- `Mesero`, `Cocina`, `Caja Restaurante` y `Admin Restaurante` llegaron con el
-- restaurante desde `database/seed.sql`, que los escribia a mano junto con sus
-- filas de `entity_permission`. Cada uno existia para cargar UNA capacidad
-- -`restaurant_waiter`, `restaurant_kitchen`, `restaurant_cashier`- que el
-- registro de modulos ya declara y que el gestor de roles ya ofrece por
-- separado. Era el mismo derecho dicho dos veces, y dicho distinto: el
-- `seed.sql` los sembraba en 15 (administrar) donde el registro dice 7 y 6.
--
-- La FUNCION no se retira. Las cuatro capacidades del restaurante siguen
-- declaradas en `app/modules/registry.py` y se conceden a cualquier rol -uno
-- nuevo, o uno que ya exista- desde el gestor de roles. Lo que desaparece es
-- el perfil vacio que no concedia nada mas.
--
-- Que pasa con los usuarios
-- -------------------------
-- Los de `Jefe de taller` pasan a `Supervisor`, que es el rol que lo absorbe y
-- que ya recibio `project_execution` en el registro: no pierden nada.
--
-- Los de los cuatro roles del restaurante NO se mueven. No hay rol destino que
-- conserve su alcance, y mandarlos a cualquier otro les daria accesos que
-- nunca tuvieron. Se quedan apuntando a un perfil retirado, o sea sin permisos
-- -- cerrado, visible y reversible: el administrador les asigna el rol nuevo
-- desde la pantalla de usuarios. La migracion los deja anotados en el log para
-- que se sepa a quien hay que reasignar.
--
-- Todo el retiro es LOGICO (`deletion_date`), asi que queda para consulta y se
-- puede revisar despues.

BEGIN;

CREATE TEMP TABLE roles_retirados AS
SELECT id_permission, permission_description
  FROM permission
 WHERE lower(permission_description) IN (
         'jefe de taller', 'mesero', 'cocina',
         'caja restaurante', 'admin restaurante'
       )
   AND deletion_date IS NULL;

-- Los usuarios de Jefe de taller pasan a Supervisor.
UPDATE "user" u
   SET id_permission = sup.id_permission,
       last_update_date = now()
  FROM roles_retirados r,
       permission sup
 WHERE u.id_permission = r.id_permission
   AND lower(r.permission_description) = 'jefe de taller'
   AND lower(sup.permission_description) = 'supervisor'
   AND sup.deletion_date IS NULL
   AND u.deletion_date IS NULL;

-- Quien queda sin rol util, para que alguien lo reasigne.
DO $$
DECLARE
    pendientes text;
BEGIN
    SELECT string_agg(u.username || ' (' || r.permission_description || ')', ', ' ORDER BY u.username)
      INTO pendientes
      FROM "user" u
      JOIN roles_retirados r ON r.id_permission = u.id_permission
     WHERE u.deletion_date IS NULL;

    IF pendientes IS NOT NULL THEN
        RAISE NOTICE 'Usuarios con un perfil retirado, hay que reasignarlos: %', pendientes;
    END IF;
END $$;

UPDATE nm_field_permission
   SET deletion_date = now(),
       last_update_date = now()
 WHERE deletion_date IS NULL
   AND id_permission IN (SELECT id_permission FROM roles_retirados);

UPDATE entity_permission
   SET deletion_date = now(),
       last_update_date = now()
 WHERE deletion_date IS NULL
   AND id_permission IN (SELECT id_permission FROM roles_retirados);

UPDATE permission
   SET deletion_date = now(),
       last_update_date = now()
 WHERE deletion_date IS NULL
   AND id_permission IN (SELECT id_permission FROM roles_retirados);

DROP TABLE roles_retirados;

-- Lo que `seed.sql` habia escrito a mano sobre el rol de administracion.
--
-- Las cuatro capacidades del restaurante quedaron en 15 -administrar- y la
-- conexion al dispositivo Kronos tambien, cuando el registro las declara en 7,
-- 6 y 2. No es un ajuste que alguien haya hecho desde el gestor: son las
-- lineas literales del `seed.sql`, que ya se retiraron de ahi en este mismo
-- cambio. Se corrigen aqui para que la base diga lo que el registro declara.
--
-- Acotado a esas cinco filas y al rol 'Administrator' a proposito: no es una
-- resiembra general, y ningun ajuste hecho desde la pantalla se toca.
UPDATE entity_permission ep
   SET control_type = v.bits::text,
       menu_label = v.etiqueta,
       last_update_date = now()
  FROM (VALUES
          ('restaurant_waiter',  7, 'Meseros'),
          ('restaurant_cashier', 7, 'Caja'),
          ('restaurant_kitchen', 6, 'Cocina'),
          ('restaurant_admin',  15, 'Admin del restaurante'),
          ('kronos_device',      2, 'Conexion al dispositivo Kronos')
       ) AS v(entidad, bits, etiqueta)
  JOIN permission p
    ON lower(p.permission_description) = 'administrator'
   AND p.deletion_date IS NULL
 WHERE ep.id_permission = p.id_permission
   AND ep.entity_name = v.entidad
   AND ep.deletion_date IS NULL
   AND ep.control_type IS DISTINCT FROM v.bits::text;

-- Lo que `seed.sql` habia escrito a mano sobre Supervisor.
--
-- El bloque "Project workflow roles" -retirado del seed.sql en este mismo
-- cambio- sembraba `task`, `task_note` y `task_type` en 15 (administrar)
-- cuando el registro concede operaciones en 7 (capturar). Solo administracion
-- borra, que es el criterio escrito de la matriz: con 15, un supervisor podia
-- borrar tareas y tipos de tarea.
--
-- Y le ponia a `task_note` una etiqueta de menu, "Notas de tarea", que el
-- registro retiro a proposito: `task_note.id_task` es NOT NULL, o sea que una
-- nota no existe sin su tarea, y con pantalla propia habia que abrir una
-- tercera lista y elegir la tarea en un desplegable para escribir una nota.
UPDATE entity_permission ep
   SET control_type = '7',
       last_update_date = now()
  FROM permission p
 WHERE ep.id_permission = p.id_permission
   AND lower(p.permission_description) = 'supervisor'
   AND p.deletion_date IS NULL
   AND ep.entity_name IN ('task', 'task_note', 'task_type')
   AND ep.deletion_date IS NULL
   AND ep.control_type IS DISTINCT FROM '7';

UPDATE entity_permission ep
   SET menu_location = 'hidden',
       menu_group = NULL,
       menu_group_icon = NULL,
       menu_label = NULL,
       last_update_date = now()
  FROM permission p
 WHERE ep.id_permission = p.id_permission
   AND p.deletion_date IS NULL
   AND ep.entity_name = 'task_note'
   AND ep.deletion_date IS NULL
   AND ep.menu_location IS DISTINCT FROM 'hidden';

COMMIT;
