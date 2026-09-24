-- Cuatro roles que no concedian nada propio.
--
-- Que se retira y por que
-- -----------------------
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
-- NO se mueven. No hay rol destino que conserve su alcance, y mandarlos a
-- cualquier otro les daria accesos que nunca tuvieron. Se quedan apuntando a
-- un perfil retirado, o sea sin permisos -- cerrado, visible y reversible: el
-- administrador les asigna el rol nuevo desde la pantalla de usuarios. La
-- migracion los deja anotados en el log para que se sepa a quien hay que
-- reasignar.
--
-- Todo el retiro es LOGICO (`deletion_date`), asi que queda para consulta y se
-- puede revisar despues.
--
-- Editado despues del commit original (ver historial)
-- -----------------------------------------------------
-- 1. `Jefe de taller` SALIO de la lista de roles a retirar. Esta migracion
--    originalmente lo fusionaba en Supervisor -razonamiento que en su momento
--    parecia correcto, medido contra la base de ese dia-, pero el rol se
--    mantuvo vivo en la rama compartida y gano funcion real (bloquear un
--    proyecto en curso, catalogo de fase del taller, separacion de deberes
--    del prevale). Como esta migracion se reaplica en cada arranque del pod,
--    dejarla como estaba habria vuelto a fusionar -y dado de baja- el rol
--    cada vez, sin importar lo que el Gestor de roles hiciera despues: es la
--    misma clase de bug que ya se encontro y corrigio en
--    `20260908100000_roles_con_los_ids_de_la_base.sql` (ver
--    `fix(permisos): Supervisor deja de resetearse en cada deploy`).
-- 2. `entity_permission.control_type` ya no existe -lo elimino
--    `20260914110000_equipos_y_alcance_por_accion.sql`, migracion posterior a
--    esta en la cadena pero anterior en el tiempo de commit-. Las dos UPDATE
--    que escribian ese campo se reescribieron contra las 4 columnas de
--    alcance (`scope_create/read/update/delete`) con la misma regla de
--    conversion que uso esa migracion: bit encendido -> Todos (4), apagado ->
--    Sin acceso (0).

BEGIN;

CREATE TEMP TABLE roles_retirados AS
SELECT id_permission, permission_description
  FROM permission
 WHERE lower(permission_description) IN (
         'mesero', 'cocina', 'caja restaurante', 'admin restaurante'
       )
   AND deletion_date IS NULL;

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
--
-- Corregido 2026-09-24: la version original comparaba el valor de HOY
-- contra el valor OBJETIVO (`IS DISTINCT FROM` contra `v.crear...`) -- eso
-- vuelve a escribir la correccion en cada reinicio del pod mientras la fila
-- no diga exactamente eso, incluyendo despues de que un administrador la
-- cambie a proposito desde el gestor. Es la misma invariante que
-- `test_no_migration_overwrites_scope_columns_via_plain_update` fija: el
-- gestor manda. Se compara en cambio contra el valor MALO conocido que dejo
-- `seed.sql` (control_type=15 en las cinco, es decir el (4,4,4,4) de estas 4
-- columnas) -- una correccion de una sola vez que deja de tocar la fila en
-- cuanto se aplica, sin importar a que la mueva despues el gestor.
UPDATE entity_permission ep
   SET scope_create = v.crear, scope_read = v.leer, scope_update = v.actualizar, scope_delete = v.borrar,
       menu_label = v.etiqueta,
       last_update_date = now()
  FROM (VALUES
          -- bits=7 (CAPTURA: crear+leer+actualizar)
          ('restaurant_waiter',  4, 4, 4, 0, 'Meseros'),
          ('restaurant_cashier', 4, 4, 4, 0, 'Caja'),
          -- bits=6 (EDITAR: leer+actualizar)
          ('restaurant_kitchen', 0, 4, 4, 0, 'Cocina'),
          -- bits=15 (TOTAL: administrar)
          ('restaurant_admin',   4, 4, 4, 4, 'Admin del restaurante'),
          -- bits=2 (CONSULTA: solo leer)
          ('kronos_device',      0, 4, 0, 0, 'Conexion al dispositivo Kronos')
       ) AS v(entidad, crear, leer, actualizar, borrar, etiqueta)
  JOIN permission p
    ON lower(p.permission_description) = 'administrator'
   AND p.deletion_date IS NULL
 WHERE ep.id_permission = p.id_permission
   AND ep.entity_name = v.entidad
   AND ep.deletion_date IS NULL
   AND (ep.scope_create, ep.scope_read, ep.scope_update, ep.scope_delete) = (4, 4, 4, 4)
   AND (ep.scope_create, ep.scope_read, ep.scope_update, ep.scope_delete)
       IS DISTINCT FROM (v.crear, v.leer, v.actualizar, v.borrar);

-- Lo que `seed.sql` habia escrito a mano sobre Supervisor -- YA NO SE FUERZA.
--
-- Esta migracion originalmente ponia `task`, `task_note` y `task_type` en 7
-- (capturar) para corregir el 15 (administrar) que `seed.sql` habia escrito a
-- mano. Correcto en su momento, pero un pedido de negocio posterior
-- (2026-09-22, ver `registry.py` y la excepcion de Supervisor en
-- `task`/`incident`) los bajo otra vez, a CONSULTA -- y como esta migracion
-- se reaplica en cada arranque del pod, forzar aqui un valor fijo habria
-- revertido esa excepcion en cada deploy, exactamente el mismo bug que
-- `fix(permisos): Supervisor deja de resetearse en cada deploy` encontro y
-- corrigio para `20260908100000_roles_con_los_ids_de_la_base.sql`. El UPDATE
-- se retira; el Gestor de roles manda sobre lo que ya existe.
--
-- La etiqueta de menu de `task_note` si se sigue ocultando abajo: eso no
-- depende de una decision de negocio que pueda cambiar por rol, es una
-- decision fija del registro (`task_note.id_task` es NOT NULL, no tiene
-- pantalla propia).
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
