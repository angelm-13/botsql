-- Permisos de campo para las entidades sembradas despues.
--
-- El hallazgo
-- -----------
-- La pantalla de facturas quedaba en blanco para cualquier usuario real. El
-- listado devolvia un solo campo -`id_invoice`- y nada mas: ni folio fiscal, ni
-- importes, ni cliente. Como el boton de descargar XML y el de actos fiscales
-- se muestran solo cuando la factura trae folio fiscal, tampoco aparecian, asi
-- que parecia que la funcionalidad no estaba.
--
-- La causa: 20260828170000 deriva los permisos de campo a partir de los
-- permisos de entidad, que es la regla correcta -si un rol puede leer una
-- entidad, puede leer sus campos-. Pero esa migracion corrio ANTES de que se
-- sembraran las 269 filas de `entity_permission` que dieron acceso a
-- facturacion, comercial, nomina y seguridad. Las entidades nuevas se quedaron
-- sin campos.
--
-- Es la misma leccion de la tanda anterior, un piso mas abajo: conceder la
-- entidad no sirve de nada si los campos no acompanan, igual que no servia
-- tener el modulo si el permiso de entidad faltaba. Y en los dos casos el
-- sintoma fue una pantalla vacia sin mensaje de error.
--
-- Se vuelve a ejecutar la misma derivacion, palabra por palabra. Es idempotente
-- por el NOT EXISTS, asi que respeta cualquier ajuste hecho a mano y solo
-- rellena lo que falta.
--
-- Nota que sigue vigente de la migracion original: la pantalla trata el bit de
-- lectura como permiso de escritura, porque el filtro del formulario se arma
-- con los campos visibles. Mientras eso siga asi no se puede conceder "ver pero
-- no editar" un campo.

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
  -- `created_by` lo fija el servicio con el usuario de la sesion: si fuera
  -- capturable, cualquiera podria atribuir un registro a otra persona.
  AND f.field_name <> 'created_by'
  AND NOT EXISTS (
    SELECT 1 FROM nm_field_permission nfp
    WHERE nfp.id_field = f.id_field
      AND nfp.id_permission = ep.id_permission
      AND nfp.deletion_date IS NULL
  );

COMMIT;
