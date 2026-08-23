BEGIN;

UPDATE proyect
SET proyect_status = 'draft', last_update_date = CURRENT_TIMESTAMP
WHERE proyect_status IS NULL
   OR lower(trim(proyect_status)) IN ('active', 'activo', 'borrador');

ALTER TABLE proyect
    ALTER COLUMN proyect_status SET DEFAULT 'draft',
    ALTER COLUMN proyect_status SET NOT NULL,
    DROP CONSTRAINT IF EXISTS ck_proyect_status;

ALTER TABLE proyect
    ADD CONSTRAINT ck_proyect_status CHECK (
        proyect_status IN (
            'draft', 'submitted', 'authorized', 'denied',
            'blocked', 'in_progress', 'stopped', 'completed'
        )
    );

CREATE TABLE IF NOT EXISTS proyect_event (
    id_proyect_event SERIAL PRIMARY KEY,
    id_proyect INTEGER NOT NULL REFERENCES proyect(id_proyect),
    id_task INTEGER REFERENCES task(id_task),
    created_by INTEGER NOT NULL REFERENCES "user"(id_user),
    author_role VARCHAR(100),
    event_type VARCHAR(30) NOT NULL CHECK (event_type IN ('created', 'status_changed', 'message', 'task_event')),
    previous_status VARCHAR(20),
    new_status VARCHAR(20),
    content TEXT,
    reason TEXT,
    review_date TIMESTAMP,
    creation_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO proyect_event (
    id_proyect, created_by, event_type, new_status, content, creation_date
)
SELECT project.id_proyect, project.created_by, 'created', project.proyect_status,
       'Registro base incorporado al historial de proyectos',
       COALESCE(project.creation_date, CURRENT_TIMESTAMP)
FROM proyect project
WHERE project.deletion_date IS NULL
  AND NOT EXISTS (
      SELECT 1 FROM proyect_event event
      WHERE event.id_proyect = project.id_proyect
  );

CREATE INDEX IF NOT EXISTS ix_proyect_event_project_date
    ON proyect_event (id_proyect, creation_date, id_proyect_event);
CREATE INDEX IF NOT EXISTS ix_proyect_event_task
    ON proyect_event (id_task) WHERE id_task IS NOT NULL;
CREATE INDEX IF NOT EXISTS ix_proyect_event_author
    ON proyect_event (created_by);
CREATE INDEX IF NOT EXISTS ix_proyect_status
    ON proyect (proyect_status) WHERE deletion_date IS NULL;
CREATE INDEX IF NOT EXISTS ix_proyect_owner
    ON proyect (created_by) WHERE deletion_date IS NULL;

WITH defaults AS (
    SELECT
        (SELECT id_user FROM "user" ORDER BY id_user LIMIT 1) AS id_user,
        (SELECT id_department FROM department ORDER BY id_department LIMIT 1) AS id_department,
        (SELECT id_subdepartment FROM subdepartment ORDER BY id_subdepartment LIMIT 1) AS id_subdepartment,
        (SELECT id_level FROM level ORDER BY id_level LIMIT 1) AS id_level
), role_names(role_name) AS (
    VALUES ('Supervisor'), ('Gerente'), ('Jefe de taller')
)
INSERT INTO permission (
    created_by, creation_date, last_update_date, authorized_by,
    permission_description, id_department, id_subdepartment, id_level
)
SELECT defaults.id_user, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, defaults.id_user,
       role_names.role_name, defaults.id_department, defaults.id_subdepartment, defaults.id_level
FROM defaults CROSS JOIN role_names
WHERE defaults.id_user IS NOT NULL
  AND NOT EXISTS (
      SELECT 1 FROM permission
      WHERE lower(permission_description) = lower(role_names.role_name)
        AND deletion_date IS NULL
  );

INSERT INTO entity_permission (
    id_permission, entity_name, control_type, menu_location, menu_group,
    menu_group_icon, menu_label, menu_order, created_by, creation_date, last_update_date
)
SELECT role.id_permission, capability.entity_name, capability.control_type,
       capability.menu_location, capability.menu_group, capability.menu_group_icon,
       capability.menu_label, capability.menu_order, role.created_by,
       CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
FROM permission role
JOIN (VALUES
    ('Supervisor', 'proyect', 7, 'sidebar', 'Operaciones', 'briefcase-business', 'Proyectos', 80),
    ('Supervisor', 'task', 15, 'sidebar', 'Operaciones', 'briefcase-business', 'Tareas', 90),
    ('Supervisor', 'task_note', 15, 'sidebar', 'Operaciones', 'briefcase-business', 'Notas de tarea', 100),
    ('Supervisor', 'task_type', 15, 'sidebar', 'Operaciones', 'briefcase-business', 'Tipos de tarea', 110),
    ('Gerente', 'proyect', 6, 'sidebar', 'Operaciones', 'briefcase-business', 'Proyectos', 80),
    ('Gerente', 'project_authorization', 2, 'hidden', NULL, NULL, NULL, 100),
    ('Jefe de taller', 'proyect', 6, 'sidebar', 'Operaciones', 'briefcase-business', 'Proyectos', 80),
    ('Jefe de taller', 'task', 15, 'sidebar', 'Operaciones', 'briefcase-business', 'Tareas', 90),
    ('Jefe de taller', 'task_note', 15, 'sidebar', 'Operaciones', 'briefcase-business', 'Notas de tarea', 100),
    ('Jefe de taller', 'task_type', 2, 'sidebar', 'Operaciones', 'briefcase-business', 'Tipos de tarea', 110),
    ('Jefe de taller', 'project_execution', 2, 'hidden', NULL, NULL, NULL, 100)
) AS capability(role_name, entity_name, control_type, menu_location, menu_group, menu_group_icon, menu_label, menu_order)
    ON lower(role.permission_description) = lower(capability.role_name)
WHERE role.deletion_date IS NULL
ON CONFLICT (id_permission, entity_name) DO UPDATE SET
    control_type = EXCLUDED.control_type,
    menu_location = EXCLUDED.menu_location,
    menu_group = EXCLUDED.menu_group,
    menu_group_icon = EXCLUDED.menu_group_icon,
    menu_label = EXCLUDED.menu_label,
    menu_order = EXCLUDED.menu_order,
    deletion_date = NULL,
    last_update_date = CURRENT_TIMESTAMP;

INSERT INTO field (table_name, field_name, created_by, creation_date, last_update_date)
SELECT column_meta.table_name, column_meta.column_name, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
FROM information_schema.columns column_meta
WHERE column_meta.table_schema = 'public'
    AND column_meta.table_name IN ('proyect', 'task', 'task_note', 'task_type')
    AND NOT EXISTS (
            SELECT 1 FROM field existing
            WHERE existing.table_name = column_meta.table_name
                AND existing.field_name = column_meta.column_name
    );

INSERT INTO nm_field_permission (
        id_field, id_permission, control_type, created_by, creation_date, last_update_date
)
SELECT field_row.id_field, role.id_permission,
             CASE
                     WHEN role.permission_description = 'Gerente' THEN '2'
                     WHEN role.permission_description = 'Jefe de taller' AND field_row.table_name IN ('proyect', 'task_type') THEN '2'
                     ELSE '15'
             END,
             role.created_by, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
FROM field field_row
JOIN permission role ON role.permission_description IN ('Supervisor', 'Gerente', 'Jefe de taller')
WHERE field_row.table_name IN ('proyect', 'task', 'task_note', 'task_type')
    AND field_row.deletion_date IS NULL
    AND role.deletion_date IS NULL
    AND (role.permission_description <> 'Gerente' OR field_row.table_name = 'proyect')
    AND NOT EXISTS (
            SELECT 1 FROM nm_field_permission existing
            WHERE existing.id_field = field_row.id_field
                AND existing.id_permission = role.id_permission
                AND existing.deletion_date IS NULL
    );

COMMIT;