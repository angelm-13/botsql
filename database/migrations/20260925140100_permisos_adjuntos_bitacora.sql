-- Permisos para `supervisor_daily_attachment` (adjuntos de la bitácora del supervisor).
--
-- La nueva entidad necesita visibilidad en el Gestor de roles y permisos, con
-- scope_create/read/update/delete para que se controle quien puede subir,
-- ver, editar y eliminar adjuntos de las bitácoras.

BEGIN;

-- Registrar campos de la tabla en el catalogo
INSERT INTO field (table_name, field_name, created_by, creation_date, last_update_date)
SELECT 'supervisor_daily_attachment', column_name, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
FROM information_schema.columns source_column
WHERE source_column.table_schema = 'public'
  AND source_column.table_name = 'supervisor_daily_attachment'
  AND NOT EXISTS (
      SELECT 1 FROM field
      WHERE field.table_name = 'supervisor_daily_attachment' AND field.field_name = source_column.column_name
  );

-- Crear permisos de supervisor_daily_attachment copiando los de supervisor_activity_log
-- Solo la PRIMERA vez que cada rol ve esta entidad. Nunca se hace UPDATE.
DO $$
BEGIN
IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'entity_permission' AND column_name = 'scope_create'
) THEN

CREATE TEMP TABLE tmp_ep_attachment AS
SELECT id_permission, 'supervisor_daily_attachment'::varchar AS entity_name,
       scope_create, scope_read, scope_update, scope_delete,
       'sidebar'::varchar AS menu_location, 'Configuracion'::varchar AS menu_group,
       'settings'::varchar AS menu_group_icon, 'Adjuntos de bitácora'::varchar AS menu_label,
       631 AS menu_order, 1 AS created_by
FROM entity_permission source_permission
WHERE source_permission.entity_name = 'supervisor_activity_log'
  AND source_permission.deletion_date IS NULL;

INSERT INTO entity_permission (
    id_permission, entity_name, scope_create, scope_read, scope_update, scope_delete,
    menu_location, menu_group, menu_group_icon, menu_label, menu_order, created_by, creation_date, last_update_date
)
SELECT source.id_permission, source.entity_name,
       source.scope_create, source.scope_read, source.scope_update, source.scope_delete,
       source.menu_location, source.menu_group,
       source.menu_group_icon, source.menu_label, source.menu_order, source.created_by, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
FROM tmp_ep_attachment source
WHERE NOT EXISTS (
    SELECT 1 FROM entity_permission target
    WHERE target.id_permission = source.id_permission AND target.entity_name = source.entity_name
);

DROP TABLE tmp_ep_attachment;

END IF;
END $$;

-- Asignar todos los campos a los roles (permisos completos: crear/leer/actualizar/eliminar)
INSERT INTO nm_field_permission (
    id_field, id_permission, control_type, created_by, creation_date, last_update_date
)
SELECT attachment_field.id_field, attachment_permission.id_permission, '15', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
FROM field attachment_field
JOIN entity_permission attachment_permission ON attachment_permission.entity_name = 'supervisor_daily_attachment'
WHERE attachment_field.table_name = 'supervisor_daily_attachment'
  AND attachment_permission.deletion_date IS NULL
  AND NOT EXISTS (
      SELECT 1 FROM nm_field_permission existing
      WHERE existing.id_field = attachment_field.id_field
        AND existing.id_permission = attachment_permission.id_permission
        AND existing.deletion_date IS NULL
  );

COMMIT;
