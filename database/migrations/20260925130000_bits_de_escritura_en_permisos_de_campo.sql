-- Corrige la derivacion de `nm_field_permission.control_type` desde
-- `entity_permission`: solo prendia el bit de lectura (scope_read), nunca
-- los de escritura (scope_create/scope_update) -- ni siquiera para una fila
-- nueva. Bug real, no solo de esta base: cualquier rol con
-- scope_create/scope_update > 0 en una entidad quedaba sin NINGUN campo
-- escribible para esa entidad en el CRUD generico, porque
-- `_field_sets_for_actor` (app/routes/task.py) filtra el payload de
-- creacion/edicion por los bits 1|4 (FIELD_WRITE_BITS) de esta tabla, no por
-- el permiso de entidad.
--
-- Sintoma real, reproducido: "Jefe de taller" tiene
-- entity_permission.task.scope_create/update = 4 (alta/edicion concedida),
-- pero al crear una tarea el payload llegaba vacio tras el filtro de campos
-- -ningun campo pasaba el chequeo de escritura-, y la ruta fallaba con
-- errors.resource_not_found (404) al no encontrar el proyecto de una tarea
-- sin id_proyect. Al editar una tarea existente pasaba lo mismo pero en
-- silencio: el PUT no cambiaba nada, sin error visible.
--
-- Como llegaron a quedar en solo-lectura: la migracion
-- 20260922100000_resembrar_catalogo_supervisor_task_incident.sql (y las
-- anteriores con el mismo patron, generadas por
-- backend/scripts/seed_module_permissions.py) da de baja un
-- nm_field_permission cuando, en el momento de esa resiembra, no encuentra
-- un entity_permission activo que lo respalde, y repone lo que falte -pero
-- solo con el bit de lectura, nunca con los de escritura-. Cualquier permiso
-- de campo con escritura concedido a mano (o heredado de un esquema
-- anterior) que pasara por ese ciclo de baja+repone quedaba degradado a
-- solo-lectura para siempre, sin que nada lo repusiera: no hay ninguna otra
-- fuente que derive los bits de escritura.
--
-- Correccion real: backend/scripts/seed_module_permissions.py ya deriva los
-- bits de escritura para lo que se sembre de aqui en adelante (ver el
-- comentario en su INSERT a nm_field_permission). Esta migracion es la
-- reparacion del dato ya sembrado con la formula vieja: sube el bit que le
-- falte a cualquier fila ACTIVA cuya entidad si tenga permiso de
-- alta/actualizacion, sin bajar nada ni tocar la visibilidad (bit 2).
--
-- Se reaplica en cada arranque del pod (sin tabla de control real, ver
-- hallazgo de infraestructura): por eso es un UPDATE por condicion, no un
-- INSERT con IDs fijos -- corre bien las veces que haga falta, y no hace
-- nada la segunda vez que ya no tenga nada que corregir.
BEGIN;

UPDATE nm_field_permission nfp
   SET control_type = (
         GREATEST(
           (CASE WHEN (nfp.control_type::integer & 2) = 2 THEN 2 ELSE 0 END)
           + (CASE WHEN ep.scope_create > 0 THEN 1 ELSE 0 END)
           + (CASE WHEN ep.scope_update > 0 THEN 4 ELSE 0 END),
           1
         )
       )::text
  FROM entity_permission ep
  JOIN field f ON f.table_name = ep.entity_name
 WHERE f.id_field = nfp.id_field
   AND ep.id_permission = nfp.id_permission
   AND ep.deletion_date IS NULL
   AND nfp.deletion_date IS NULL
   AND nfp.control_type::integer <> GREATEST(
         (CASE WHEN (nfp.control_type::integer & 2) = 2 THEN 2 ELSE 0 END)
         + (CASE WHEN ep.scope_create > 0 THEN 1 ELSE 0 END)
         + (CASE WHEN ep.scope_update > 0 THEN 4 ELSE 0 END),
         1
       );

COMMIT;
