-- Dos cosas nuevas, sin relacion entre si salvo que ambas cuelgan de un
-- proyecto de taller:
--
-- 1. `customer_contact`: el catalogo de contactos por empresa que
--    20260911180000 dijo que faltaba (ver el comentario de `requested_by`
--    en ese archivo). El campo "Cliente" del proyecto pasa a ser este
--    selector -"Empresa - Contacto"-, y de el se derivan tanto
--    `id_customer_supplier` como `requested_by` (que se queda como snapshot
--    del nombre al momento de guardar, no como referencia viva).
--
-- 2. `proyect_document`: adjuntos (PDF/DOCX) de requerimientos de un
--    proyecto de taller especifico. Aparte del modulo /document generico
--    porque ese usa `user.id_proyect` del JWT -el tenant/instalacion, la
--    MISMA tabla `proyect` pero otro significado- y no el proyecto que se
--    esta editando en el formulario.

BEGIN;

-- --- 1. contactos por empresa -------------------------------------------

CREATE TABLE IF NOT EXISTS customer_contact (
    id_customer_contact SERIAL PRIMARY KEY,
    id_customer_supplier INTEGER NOT NULL REFERENCES customer_supplier(id_customer_supplier),
    full_name            VARCHAR(150) NOT NULL,
    email                VARCHAR(100),
    phone                VARCHAR(30),
    position             VARCHAR(80),
    status               VARCHAR(20) NOT NULL DEFAULT 'activo'
                             CHECK (status IN ('activo', 'inactivo')),
    created_by           INTEGER NOT NULL REFERENCES "user"(id_user),
    creation_date        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_update_date     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deletion_date        TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_customer_contact_customer
    ON customer_contact(id_customer_supplier) WHERE deletion_date IS NULL;

ALTER TABLE proyect
    ADD COLUMN IF NOT EXISTS id_customer_contact INTEGER
        REFERENCES customer_contact(id_customer_contact);

CREATE INDEX IF NOT EXISTS idx_proyect_customer_contact
    ON proyect (id_customer_contact) WHERE id_customer_contact IS NOT NULL;

INSERT INTO field (table_name, field_name, created_by, creation_date, last_update_date)
SELECT 'customer_contact', column_name, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
FROM information_schema.columns source_column
WHERE source_column.table_schema = 'public'
  AND source_column.table_name = 'customer_contact'
  AND NOT EXISTS (
      SELECT 1 FROM field
      WHERE field.table_name = 'customer_contact' AND field.field_name = source_column.column_name
  );

-- Sembrado de entity_permission, copiando el scope de customer_supplier por
-- rol -- solo la PRIMERA vez que cada rol ve esta entidad nueva. Nunca se
-- hace UPDATE de una fila que ya existe: el Gestor de roles y permisos manda
-- sobre lo que un administrador ya haya ajustado a mano, y una migracion que
-- reescriba scope_* en cada reinicio del pod se lo llevaria por delante en
-- el siguiente despliegue (ver test_manager_wins.py).
DO $$
BEGIN
IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'entity_permission' AND column_name = 'scope_create'
) THEN

CREATE TEMP TABLE tmp_ep_customer_contact AS
SELECT id_permission, 'customer_contact'::varchar AS entity_name,
       scope_create, scope_read, scope_update, scope_delete,
       'sidebar'::varchar AS menu_location, 'CRM'::varchar AS menu_group,
       'users'::varchar AS menu_group_icon, 'Contactos'::varchar AS menu_label,
       625 AS menu_order, 1 AS created_by
FROM entity_permission source_permission
WHERE source_permission.entity_name = 'customer_supplier'
  AND source_permission.deletion_date IS NULL;

INSERT INTO entity_permission (
    id_permission, entity_name, scope_create, scope_read, scope_update, scope_delete,
    menu_location, menu_group, menu_group_icon, menu_label, menu_order, created_by, creation_date, last_update_date
)
SELECT source.id_permission, source.entity_name,
       source.scope_create, source.scope_read, source.scope_update, source.scope_delete,
       source.menu_location, source.menu_group,
       source.menu_group_icon, source.menu_label, source.menu_order, source.created_by, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
FROM tmp_ep_customer_contact source
WHERE NOT EXISTS (
    SELECT 1 FROM entity_permission target
    WHERE target.id_permission = source.id_permission AND target.entity_name = source.entity_name
);

DROP TABLE tmp_ep_customer_contact;

END IF;
END $$;

INSERT INTO nm_field_permission (
    id_field, id_permission, control_type, created_by, creation_date, last_update_date
)
SELECT contact_field.id_field, contact_permission.id_permission, '15', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
FROM field contact_field
JOIN entity_permission contact_permission ON contact_permission.entity_name = 'customer_contact'
WHERE contact_field.table_name = 'customer_contact'
  AND contact_permission.deletion_date IS NULL
  AND NOT EXISTS (
      SELECT 1 FROM nm_field_permission existing
      WHERE existing.id_field = contact_field.id_field
        AND existing.id_permission = contact_permission.id_permission
        AND existing.deletion_date IS NULL
  );

-- --- 2. adjuntos del proyecto ---------------------------------------------
-- Ligero a proposito: una fila por archivo, sin versiones -- si se quiere
-- reemplazar un requerimiento se borra el viejo y se sube el nuevo. El
-- modulo /document SI versiona, pero es justo lo que no aplica aqui.

CREATE TABLE IF NOT EXISTS proyect_document (
    id_proyect_document SERIAL PRIMARY KEY,
    id_proyect          INTEGER NOT NULL REFERENCES proyect(id_proyect),
    title                VARCHAR(200),
    file_path            VARCHAR(400) NOT NULL,
    original_filename    VARCHAR(255) NOT NULL,
    extension            VARCHAR(10) NOT NULL,
    mime_type            VARCHAR(120) NOT NULL,
    file_size            INTEGER NOT NULL,
    sha256               VARCHAR(64) NOT NULL,
    created_by           INTEGER NOT NULL REFERENCES "user"(id_user),
    creation_date        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_update_date     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deletion_date        TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_proyect_document_proyect
    ON proyect_document(id_proyect) WHERE deletion_date IS NULL;

-- El expediente registra que se subio/quito un adjunto en la misma bitacora
-- que el resto del historial del proyecto (mismo patron que
-- 20260911180000 amplio la lista para 'management_transition' etc).
--
-- Este DROP+ADD corre en CADA arranque del pod (sin tabla de control) y
-- angosta el constraint a exactamente esta lista cada vez -- si una
-- migracion MAS NUEVA (20260924190000: task_status_changed/task_note) ya
-- amplio esta misma columna y una fila real llego a usar uno de esos
-- valores, esta migracion la revierte primero (corre antes por fecha) y
-- truena con CheckViolation/CrashLoopBackOff. Asi tumbo tyakxa-dev el
-- 2026-09-24 con `ck_proyect_status` (mismo patron, otra columna). La lista
-- de aqui en adelante es la FINAL, identica a la de 20260911180000 y
-- 20260924190000 -- si vuelve a crecer, hay que actualizar las tres a la
-- vez.
ALTER TABLE proyect_event DROP CONSTRAINT IF EXISTS proyect_event_event_type_check;

ALTER TABLE proyect_event ADD CONSTRAINT proyect_event_event_type_check CHECK (
    event_type IN (
        'created', 'status_changed', 'message', 'task_event',
        'management_transition', 'payment_agreed', 'payment_settled',
        'document_attached', 'document_removed',
        'task_status_changed', 'task_note'
    )
);

COMMIT;
