-- Avisos tambien por correo (2026-11-05): cada aviso de la campana se manda al
-- correo de quien lo recibe, si tiene uno y no lo apago. El correo del usuario
-- sigue siendo opcional. Idempotente: se reaplica en cada arranque.
BEGIN;

ALTER TABLE notification ADD COLUMN IF NOT EXISTS email_sent_at TIMESTAMP;

ALTER TABLE "user"
    ADD COLUMN IF NOT EXISTS receive_email_notifications BOOLEAN NOT NULL DEFAULT TRUE;

-- El campo en el catalogo y, por rol, el mismo permiso que ya tiene el correo.
INSERT INTO field (table_name, field_name, created_by, creation_date, last_update_date)
SELECT 'user', 'receive_email_notifications', COALESCE((SELECT MIN(id_user) FROM "user"), 1), CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE EXISTS (SELECT 1 FROM "user")
  AND NOT EXISTS (
      SELECT 1 FROM field WHERE table_name = 'user' AND field_name = 'receive_email_notifications'
  );

INSERT INTO nm_field_permission (
    id_field, id_permission, control_type, created_by, creation_date, last_update_date
)
SELECT nuevo.id_field, permission.id_permission, source.control_type,
       COALESCE((SELECT MIN(id_user) FROM "user"), 1), CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
FROM field AS nuevo
CROSS JOIN permission
LEFT JOIN LATERAL (
    SELECT MAX(existing.control_type) AS control_type
    FROM nm_field_permission AS existing
    JOIN field AS source_field ON source_field.id_field = existing.id_field
    WHERE existing.id_permission = permission.id_permission
      AND existing.deletion_date IS NULL
      AND source_field.table_name = 'user'
      AND source_field.field_name = 'email'
) AS source ON TRUE
WHERE nuevo.table_name = 'user'
  AND nuevo.field_name = 'receive_email_notifications'
  AND source.control_type IS NOT NULL
  AND NOT EXISTS (
      SELECT 1 FROM nm_field_permission AS actual
      WHERE actual.id_field = nuevo.id_field
        AND actual.id_permission = permission.id_permission
        AND actual.deletion_date IS NULL
  );

COMMIT;
