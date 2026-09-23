-- Permisos de campo para que los roles puedan capturar.
--
-- Las pantallas genericas filtran el formulario por `nm_field_permission`: un
-- usuario que no es administrador solo puede leer y escribir los campos que su
-- rol tenga concedidos. La tabla estaba practicamente vacia -una sola fila-,
-- asi que cualquier rol no administrador veia el formulario recortado y su
-- captura llegaba al servidor sin datos.
--
-- El permiso de campo se deriva del permiso de entidad que el rol ya tiene:
-- si un rol puede leer y editar productos, obtiene los campos de producto con
-- ese mismo alcance. Asi no hay dos fuentes de verdad que se puedan
-- contradecir, y conceder una entidad nueva a un rol arrastra sus campos.
--
-- Quedan fuera:
--
--   * Las columnas que el sistema administra (fecha de alta, de cambio y de
--     baja) ya no estan en el catalogo `field`.
--   * `created_by`, que lo fija el servicio con el usuario de la sesion: si
--     fuera capturable, cualquiera podria atribuir un registro a otra persona.
--
-- Nota sobre el modelo actual: la pantalla trata el bit de lectura como
-- permiso de escritura, porque el filtro del formulario se arma con los campos
-- visibles. Mientras eso siga asi, no se puede conceder "ver pero no editar"
-- un campo; se deja anotado.

BEGIN;

-- Guardado con un chequeo de existencia de scope_create: esta migracion es
-- anterior a 20260914110000_equipos_y_alcance_por_accion.sql, que agrega esas
-- 4 columnas y suelta control_type mas adelante en la misma pasada. Sin este
-- guardado, la primera pasada completa contra un volumen nuevo tronaria aqui
-- con "column scope_create does not exist" -aunque el destino de este INSERT
-- es nm_field_permission.control_type (que no cambia), la fuente lee
-- entity_permission.scope_*-. En pasadas posteriores la columna ya existe y
-- el INSERT corre normal.
DO $$
BEGIN
IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'entity_permission' AND column_name = 'scope_create'
) THEN

INSERT INTO nm_field_permission (id_field, id_permission, control_type, created_by)
SELECT f.id_field,
       ep.id_permission,
       -- Se hereda el alcance que el rol ya tiene sobre la entidad, recompuesto
       -- como bitmask (1 crear, 2 leer, 4 actualizar, 8 borrar) a partir de las
       -- cuatro columnas de scope_* (0 = sin acceso, distinto de 0 = con
       -- acceso) desde que 20260914110000_equipos_y_alcance_por_accion.sql
       -- reemplazo entity_permission.control_type.
       LEAST(
           (CASE WHEN ep.scope_create <> 0 THEN 1 ELSE 0 END) +
           (CASE WHEN ep.scope_read   <> 0 THEN 2 ELSE 0 END) +
           (CASE WHEN ep.scope_update <> 0 THEN 4 ELSE 0 END) +
           (CASE WHEN ep.scope_delete <> 0 THEN 8 ELSE 0 END),
           15
       )::text,
       1
FROM entity_permission ep
JOIN field f
  ON f.table_name = ep.entity_name
 AND f.deletion_date IS NULL
WHERE ep.deletion_date IS NULL
  AND f.field_name <> 'created_by'
  AND NOT EXISTS (
    SELECT 1 FROM nm_field_permission nfp
    WHERE nfp.id_field = f.id_field
      AND nfp.id_permission = ep.id_permission
      AND nfp.deletion_date IS NULL
  );

END IF;
END $$;

COMMIT;
