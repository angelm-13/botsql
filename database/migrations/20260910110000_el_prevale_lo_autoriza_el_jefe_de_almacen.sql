-- Separacion de deberes en los vales de material.
--
-- Lo que se pidio
-- ---------------
-- Quien administra el sistema puede dejar el PREVALE -- el material pedido, en
-- borrador -- pero no emitir el vale. El material lo suelta el jefe de almacen,
-- y es ese acto el que mueve la existencia.
--
-- Como estaban las filas antes de esto (medido, no supuesto):
--
--     rol                    entidad                       bits
--     ---------------------- ----------------------------- ----
--     1 Administrator        warehouse_voucher                3   <- podia crear
--     2 Supervisor           warehouse_prevoucher             7
--     5 Almacenista          warehouse_voucher                7
--     6 Jefe de almacen      warehouse_voucher                7
--     5, 6                   warehouse_voucher_confirm        2
--
-- El Administrator podia crear vales (bit 1) y NO tenia fila de prevale: podia
-- surtirse y no podia pedir, que es exactamente al reves de lo que se quiere. Y
-- `warehouse_voucher_authorize` no existia: no habia con que distinguir surtir
-- de autorizar.
--
-- Que hace
-- --------
--   1. crea `warehouse_voucher_authorize` para el jefe de almacen (rol 6);
--   2. le da al Administrator su fila de prevale, que le faltaba;
--   3. le quita al Administrator el bit de CREAR vales, dejandole el resto.
--
-- Por que se toca una fila viva, contra la regla de "el gestor manda"
-- -------------------------------------------------------------------
-- Porque el cambio de permisos ES lo que se pidio. La regla existe para que un
-- despliegue no revierta lo que un administrador configuro a mano; aqui la
-- instruccion viene de fuera y es explicita, igual que en la renumeracion de
-- roles de 20260908100000. Se acota al bit de crear y al rol 1: ni se retira la
-- fila -- el Administrator sigue viendo y leyendo los vales -- ni se toca
-- ningun otro rol.
--
-- La cuenta `admin1` no se ve afectada por nada de esto: es el bootstrap admin
-- y `_sin_restriccion` la deja pasar antes de mirar una sola fila de permiso.
-- Esto gobierna a cualquier OTRO usuario que lleve el rol Administrator.

BEGIN;

-- Guardado con un chequeo de existencia de scope_create: esta migracion es
-- anterior a 20260914110000_equipos_y_alcance_por_accion.sql, que agrega esas
-- 4 columnas y suelta control_type mas adelante en la misma pasada. Sin este
-- guardado, la primera pasada completa contra un volumen nuevo tronaria en
-- las tres secciones con "column scope_create does not exist".
DO $$
BEGIN
IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'entity_permission' AND column_name = 'scope_create'
) THEN

-- 1. La capacidad de autorizar, para el jefe de almacen.
--
-- Con bits de CAPTURA (7) y no los 2 de una capacidad oculta cualquiera: la
-- ruta `POST /vouchers/<id>/authorize` se guarda con `create`, y con solo
-- lectura el jefe de almacen recibiria un 403 en la puerta.
INSERT INTO entity_permission (
    id_permission, entity_name, scope_create, scope_read, scope_update, scope_delete, menu_location,
    menu_group, menu_group_icon, menu_label, menu_order, created_by
)
SELECT 6, 'warehouse_voucher_authorize', 4, 4, 4, 0, 'hidden',
       NULL, NULL, NULL, 290, 1
WHERE EXISTS (SELECT 1 FROM permission WHERE id_permission = 6)
  AND NOT EXISTS (
      SELECT 1 FROM entity_permission
      WHERE id_permission = 6
        AND entity_name = 'warehouse_voucher_authorize'
  );

-- 2. El prevale para el Administrator, que no lo tenia.
--
-- Sin esta fila, quitarle el bit de crear vales lo dejaria sin poder ni pedir
-- ni surtir: no podria hacer nada con los vales, que no es lo que se pidio.
INSERT INTO entity_permission (
    id_permission, entity_name, scope_create, scope_read, scope_update, scope_delete, menu_location,
    menu_group, menu_group_icon, menu_label, menu_order, created_by
)
SELECT 1, 'warehouse_prevoucher', 4, 4, 4, 0, 'sidebar',
       'Almacen', 'package', 'Prevales de material', 285, 1
WHERE EXISTS (SELECT 1 FROM permission WHERE id_permission = 1)
  AND NOT EXISTS (
      SELECT 1 FROM entity_permission
      WHERE id_permission = 1
        AND entity_name = 'warehouse_prevoucher'
  );

-- 3. Y se le retira el bit de CREAR vales.
--
-- Desde 20260914110000_equipos_y_alcance_por_accion.sql el bit de crear vive
-- en su propia columna `scope_create` (0 sin acceso, 4 Todos), asi que ya no
-- hace falta la aritmetica de bits sobre un TEXT.
--
-- Acotado a que el alcance de crear este puesto, para que la migracion se
-- pueda reaplicar -- `db-migrate` la corre en cada arranque -- sin volver a
-- escribir una fila que ya esta como debe.
UPDATE entity_permission
   SET scope_create = 0,
       last_update_date = now()
 WHERE id_permission = 1
   AND entity_name = 'warehouse_voucher'
   AND deletion_date IS NULL
   AND scope_create <> 0;

END IF;
END $$;

COMMIT;
