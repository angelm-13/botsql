BEGIN;

ALTER TABLE "user"
    ADD COLUMN IF NOT EXISTS is_employee BOOLEAN NOT NULL DEFAULT FALSE;

UPDATE "user"
SET is_employee = TRUE
WHERE user_type = 'employee'
  AND is_employee = FALSE;

INSERT INTO field (table_name, field_name, created_by, creation_date, last_update_date)
SELECT 'user', 'is_employee', COALESCE((SELECT MIN(id_user) FROM "user"), 1), CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE EXISTS (SELECT 1 FROM "user")
  AND NOT EXISTS (
      SELECT 1 FROM field
      WHERE table_name = 'user' AND field_name = 'is_employee'
  );

INSERT INTO nm_field_permission (
    id_field, id_permission, control_type, created_by, creation_date, last_update_date
)
SELECT employee_field.id_field, permission.id_permission, source.control_type,
       COALESCE((SELECT MIN(id_user) FROM "user"), 1), CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
FROM field AS employee_field
CROSS JOIN permission
LEFT JOIN LATERAL (
    SELECT MAX(existing.control_type) AS control_type
    FROM nm_field_permission AS existing
    JOIN field AS source_field ON source_field.id_field = existing.id_field
    WHERE existing.id_permission = permission.id_permission
      AND existing.deletion_date IS NULL
      AND source_field.table_name = 'user'
      AND source_field.field_name = 'puesto'
) AS source ON TRUE
WHERE employee_field.table_name = 'user'
  AND employee_field.field_name = 'is_employee'
  AND source.control_type IS NOT NULL
  AND NOT EXISTS (
      SELECT 1 FROM nm_field_permission AS current_permission
      WHERE current_permission.id_field = employee_field.id_field
        AND current_permission.id_permission = permission.id_permission
        AND current_permission.deletion_date IS NULL
  );

COMMIT;