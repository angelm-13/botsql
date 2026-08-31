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

INSERT INTO nm_field_permission (id_field, id_permission, control_type, created_by)
SELECT f.id_field,
       ep.id_permission,
       -- Se hereda el alcance que el rol ya tiene sobre la entidad.
       LEAST(ep.control_type, 15)::text,
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

COMMIT;
