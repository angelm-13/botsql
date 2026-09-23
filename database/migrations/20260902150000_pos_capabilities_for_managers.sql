-- Devolver las capacidades del punto de venta a los roles que el registro les da.
--
-- Que paso
-- --------
-- `20260901000000_module_permission_matrix_licensed.sql` se genero desde una
-- version del registro anterior a la integracion del punto de venta, asi que
-- solo concede `pos_terminal` y `pos_admin` al rol 1. El registro mezclado los
-- da tambien al 2 y al 16. Como esa matriz da de baja todo lo vigente antes de
-- sembrar -y corre en cada arranque del pod-, cada despliegue dejaba a esos dos
-- roles sin punto de venta.
--
-- Por que esta migracion y no regenerar la matriz
-- -----------------------------------------------
-- Regenerarla desde el registro mezclado arreglaba el punto de venta y rompia
-- otra cosa: el registro no concede los modulos `documentos` ni `laboratorio` a
-- ningun rol -sus filas las siembra 20260901090000 aparte- y la matriz da de
-- baja todo lo que no esta en ella. Habria matado Documentos y Laboratorio en
-- cada despliegue.
--
-- Dos mecanismos sembrando la misma tabla se pisan segun el orden en que corran.
-- Esta migracion no lo resuelve, solo corrige la diferencia concreta; va
-- despues de la matriz por su fecha, asi que sobrevive al resembrado. Unificar
-- los dos mecanismos es una decision aparte.
--
-- Se usa ON CONFLICT y no INSERT: la restriccion unica es por (perfil, entidad)
-- sin importar la baja logica, asi que hay que reactivar la fila en vez de
-- insertar otra.

BEGIN;

-- Guardado con un chequeo de existencia de scope_create: esta migracion es
-- anterior a 20260914110000_equipos_y_alcance_por_accion.sql, que agrega esas
-- 4 columnas y suelta control_type mas adelante en la misma pasada. Sin este
-- guardado, la primera pasada completa contra un volumen nuevo tronaria aqui
-- con "column scope_create does not exist".
DO $$
BEGIN
IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'entity_permission' AND column_name = 'scope_create'
) THEN

INSERT INTO entity_permission (
    id_permission, entity_name, scope_create, scope_read, scope_update, scope_delete, menu_location, menu_group,
    menu_group_icon, menu_label, menu_order, created_by
)
SELECT rol.id_permission, cap.entity_name,
       cap.scope_create, cap.scope_read, cap.scope_update, cap.scope_delete,
       'sidebar', 'Punto de venta', 'pos', cap.menu_label, 640,
       COALESCE((SELECT MIN(id_user) FROM "user"), 1)
FROM (VALUES (2), (16)) AS rol(id_permission)
CROSS JOIN (VALUES
    -- control_type original -> scope_create/scope_read/scope_update/scope_delete
    -- (misma conversion que 20260914110000_equipos_y_alcance_por_accion.sql)
    ('pos_admin', 4, 4, 4, 4, 'Admin del punto de venta'),
    ('pos_terminal', 4, 4, 4, 0, 'Caja del punto de venta')
) AS cap(entity_name, scope_create, scope_read, scope_update, scope_delete, menu_label)
WHERE EXISTS (SELECT 1 FROM permission WHERE permission.id_permission = rol.id_permission)
  AND EXISTS (SELECT 1 FROM "user")
-- El gestor manda: aqui NO se pisa la fila que ya existe.
--
-- Una fila viva es del administrador y pisarla revierte su trabajo; una de baja
-- significa que la quito a proposito, y reactivarla devolveria un acceso
-- retirado. El registro solo da el valor por omision al par (perfil, entidad)
-- que todavia no existe.
ON CONFLICT (id_permission, entity_name) DO NOTHING;

END IF;
END $$;

COMMIT;
