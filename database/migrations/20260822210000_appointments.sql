BEGIN;

CREATE EXTENSION IF NOT EXISTS btree_gist;

CREATE TABLE IF NOT EXISTS calendar_profile (
    id_calendar_profile SERIAL PRIMARY KEY,
    id_user INTEGER NOT NULL REFERENCES "user"(id_user),
    id_proyect INTEGER NOT NULL REFERENCES proyect(id_proyect),
    calendar_code VARCHAR(80) NOT NULL UNIQUE,
    display_name VARCHAR(150) NOT NULL,
    timezone VARCHAR(64) NOT NULL DEFAULT 'UTC',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_by INTEGER NOT NULL REFERENCES "user"(id_user),
    creation_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_update_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deletion_date TIMESTAMP
);

CREATE TABLE IF NOT EXISTS appointment_type (
    id_appointment_type SERIAL PRIMARY KEY,
    id_calendar_profile INTEGER NOT NULL REFERENCES calendar_profile(id_calendar_profile),
    name VARCHAR(120) NOT NULL,
    description TEXT,
    duration_minutes INTEGER NOT NULL CHECK (duration_minutes BETWEEN 5 AND 480),
    buffer_before_minutes INTEGER NOT NULL DEFAULT 0 CHECK (buffer_before_minutes BETWEEN 0 AND 240),
    buffer_after_minutes INTEGER NOT NULL DEFAULT 0 CHECK (buffer_after_minutes BETWEEN 0 AND 240),
    minimum_notice_minutes INTEGER NOT NULL DEFAULT 0 CHECK (minimum_notice_minutes >= 0),
    booking_horizon_days INTEGER NOT NULL DEFAULT 60 CHECK (booking_horizon_days BETWEEN 1 AND 365),
    meeting_provider VARCHAR(20) NOT NULL DEFAULT 'none' CHECK (meeting_provider IN ('none', 'google', 'microsoft', 'zoom')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_by INTEGER NOT NULL REFERENCES "user"(id_user),
    creation_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_update_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deletion_date TIMESTAMP
);

CREATE TABLE IF NOT EXISTS availability_rule (
    id_availability_rule SERIAL PRIMARY KEY,
    id_calendar_profile INTEGER NOT NULL REFERENCES calendar_profile(id_calendar_profile),
    weekday SMALLINT NOT NULL CHECK (weekday BETWEEN 0 AND 6),
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_by INTEGER NOT NULL REFERENCES "user"(id_user),
    creation_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deletion_date TIMESTAMP,
    CHECK (start_time < end_time)
);

CREATE TABLE IF NOT EXISTS availability_override (
    id_availability_override SERIAL PRIMARY KEY,
    id_calendar_profile INTEGER NOT NULL REFERENCES calendar_profile(id_calendar_profile),
    override_date DATE NOT NULL,
    start_time TIME,
    end_time TIME,
    is_available BOOLEAN NOT NULL DEFAULT FALSE,
    created_by INTEGER NOT NULL REFERENCES "user"(id_user),
    creation_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deletion_date TIMESTAMP,
    CHECK (NOT is_available OR (start_time IS NOT NULL AND end_time IS NOT NULL AND start_time < end_time))
);

CREATE TABLE IF NOT EXISTS appointment (
    id_appointment SERIAL PRIMARY KEY,
    id_calendar_profile INTEGER NOT NULL REFERENCES calendar_profile(id_calendar_profile),
    id_appointment_type INTEGER NOT NULL REFERENCES appointment_type(id_appointment_type),
    id_proyect INTEGER NOT NULL REFERENCES proyect(id_proyect),
    guest_name VARCHAR(150) NOT NULL,
    guest_email VARCHAR(254) NOT NULL,
    guest_notes TEXT,
    starts_at TIMESTAMPTZ NOT NULL,
    ends_at TIMESTAMPTZ NOT NULL,
    guest_timezone VARCHAR(64) NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'confirmed' CHECK (status IN ('pending_confirmation', 'confirmed', 'completed', 'cancelled', 'no_show', 'integration_failed')),
    meeting_provider VARCHAR(20) NOT NULL DEFAULT 'none' CHECK (meeting_provider IN ('none', 'google', 'microsoft', 'zoom')),
    meeting_url VARCHAR(1000),
    external_status VARCHAR(30) NOT NULL DEFAULT 'not_required',
    management_token_hash VARCHAR(64) NOT NULL UNIQUE,
    created_by INTEGER NOT NULL REFERENCES "user"(id_user),
    creation_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_update_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    cancellation_date TIMESTAMP,
    CHECK (starts_at < ends_at)
);

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ex_appointment_no_overlap') THEN
        ALTER TABLE appointment ADD CONSTRAINT ex_appointment_no_overlap
            EXCLUDE USING gist (
                id_calendar_profile WITH =,
                tstzrange(starts_at, ends_at, '[)') WITH &&
            ) WHERE (status IN ('pending_confirmation', 'confirmed'));
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_calendar_profile_owner ON calendar_profile (id_user, id_proyect) WHERE deletion_date IS NULL;
CREATE INDEX IF NOT EXISTS ix_appointment_type_profile ON appointment_type (id_calendar_profile) WHERE deletion_date IS NULL;
CREATE INDEX IF NOT EXISTS ix_availability_rule_profile_day ON availability_rule (id_calendar_profile, weekday) WHERE deletion_date IS NULL;
CREATE INDEX IF NOT EXISTS ix_availability_override_profile_date ON availability_override (id_calendar_profile, override_date) WHERE deletion_date IS NULL;
CREATE INDEX IF NOT EXISTS ix_appointment_project_start ON appointment (id_proyect, starts_at);

-- Guardado con un chequeo de existencia de scope_create: esta migracion es
-- anterior a 20260914110000_equipos_y_alcance_por_accion.sql (que agrega las
-- 4 columnas de alcance y suelta control_type), asi que en la PRIMERA pasada
-- completa contra un volumen nuevo todavia no existen -las agrega esa misma
-- migracion, mas adelante en la misma pasada-. Sin este guardado, la primera
-- pasada tronaria aqui con "column scope_create does not exist" antes de
-- llegar siquiera a la migracion que las crea. En pasadas posteriores (o en
-- cualquier base que ya paso por 20260914110000) la columna ya existe y el
-- bloque corre normal; si de verdad falta la fila para esta entidad se
-- resiembra sola en el siguiente reinicio del pod, que es cuando esta
-- condicion pasa a ser verdadera.
DO $$
BEGIN
IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'entity_permission' AND column_name = 'scope_create'
) THEN

CREATE TEMP TABLE tmp_ep_appointments AS
-- control_type original 15 (los 4 bits encendidos) -> las 4 columnas de
-- alcance en "Todos" (4), misma conversion que
-- 20260914110000_equipos_y_alcance_por_accion.sql. scope_create/read/update/
-- delete ya son SMALLINT NOT NULL desde esa migracion, sin la ambiguedad
-- text/smallint que tenia control_type.
SELECT permission.id_permission, 'appointment'::varchar AS entity_name,
       4 AS scope_create, 4 AS scope_read, 4 AS scope_update, 4 AS scope_delete,
       'sidebar'::varchar AS menu_location, 'Operaciones'::varchar AS menu_group,
       'calendar-days'::varchar AS menu_group_icon, 'Calendario'::varchar AS menu_label,
       75 AS menu_order, permission.created_by
FROM permission
WHERE permission.deletion_date IS NULL
    AND lower(permission.permission_description) IN ('supervisor', 'gerente');

UPDATE entity_permission target SET
    scope_create = source.scope_create,
    scope_read = source.scope_read,
    scope_update = source.scope_update,
    scope_delete = source.scope_delete,
    menu_location = source.menu_location,
    menu_group = source.menu_group,
    menu_group_icon = source.menu_group_icon,
    menu_label = source.menu_label,
    menu_order = source.menu_order,
    deletion_date = NULL,
    last_update_date = CURRENT_TIMESTAMP
FROM tmp_ep_appointments source
WHERE target.id_permission = source.id_permission
  AND target.entity_name = source.entity_name;

INSERT INTO entity_permission (
    id_permission, entity_name, scope_create, scope_read, scope_update, scope_delete, menu_location, menu_group,
    menu_group_icon, menu_label, menu_order, created_by, creation_date, last_update_date
)
SELECT source.id_permission, source.entity_name,
       source.scope_create, source.scope_read, source.scope_update, source.scope_delete,
       source.menu_location, source.menu_group,
       source.menu_group_icon, source.menu_label, source.menu_order, source.created_by, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
FROM tmp_ep_appointments source
WHERE NOT EXISTS (
    SELECT 1 FROM entity_permission target
    WHERE target.id_permission = source.id_permission AND target.entity_name = source.entity_name
);

DROP TABLE tmp_ep_appointments;
END IF;
END $$;


COMMIT;