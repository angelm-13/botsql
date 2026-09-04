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

INSERT INTO entity_permission (
    id_permission, entity_name, control_type, menu_location, menu_group,
    menu_group_icon, menu_label, menu_order, created_by
)
SELECT rol.id_permission, cap.entity_name, cap.control_type,
       'sidebar', 'Punto de venta', 'pos', cap.menu_label, 640,
       COALESCE((SELECT MIN(id_user) FROM "user"), 1)
FROM (VALUES (2), (16)) AS rol(id_permission)
CROSS JOIN (VALUES
    ('pos_admin', 15, 'Admin del punto de venta'),
    ('pos_terminal', 7, 'Caja del punto de venta')
) AS cap(entity_name, control_type, menu_label)
WHERE EXISTS (SELECT 1 FROM permission WHERE permission.id_permission = rol.id_permission)
  AND EXISTS (SELECT 1 FROM "user")
ON CONFLICT (id_permission, entity_name) DO UPDATE
   SET control_type = EXCLUDED.control_type,
       menu_location = EXCLUDED.menu_location,
       menu_group = EXCLUDED.menu_group,
       menu_group_icon = EXCLUDED.menu_group_icon,
       menu_label = EXCLUDED.menu_label,
       menu_order = EXCLUDED.menu_order,
       deletion_date = NULL,
       last_update_date = now();

COMMIT;
