-- Red de seguridad de idempotencia para el modulo de citas
-- (20260822210000_appointments.sql, 20260822211000_appointment_buffers.sql,
-- 20260822212000_appointment_notifications.sql).
--
-- Esos tres archivos usan CREATE TABLE / ADD COLUMN / ADD CONSTRAINT sin
-- ninguna guarda. Si alguna de esas tres migraciones llegara a reintentarse
-- contra una base donde sus objetos ya existen (por ejemplo, una base cuyo
-- registro en schema_migration se perdio o nunca se sincronizo con lo que en
-- realidad ya tiene el esquema), Postgres responde "already exists" y
-- apply_migrations.py detiene ahi todo el proceso.
--
-- No se corrigen esos tres archivos directamente: ya se aplicaron en
-- tyakxa-dev/torredigital-prod/adser-prod, y apply_migrations.py detiene el
-- proceso completo si el contenido de una migracion ya aplicada cambia
-- (compara checksum). Esta migracion nueva es un duplicado defensivo: repite
-- las mismas definiciones con IF NOT EXISTS / guardas, asi que en cualquier
-- base donde los objetos ya existen es un no-op completo, y solo actua si de
-- verdad falta algo.

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

-- Columnas de appointment_buffers.sql: se agregan (o confirman) ANTES de
-- tocar el constraint de solapamiento, porque su definicion final depende
-- de ellas.
ALTER TABLE appointment
    ADD COLUMN IF NOT EXISTS blocked_starts_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS blocked_ends_at TIMESTAMPTZ;

-- Solo backfillea filas recien agregadas (columna aun en NULL); nunca pisa
-- un blocked_starts_at/ends_at que ya haya divergido de starts_at/ends_at
-- por el uso normal de la aplicacion.
UPDATE appointment
SET blocked_starts_at = starts_at,
    blocked_ends_at = ends_at
WHERE blocked_starts_at IS NULL;

ALTER TABLE appointment
    ALTER COLUMN blocked_starts_at SET NOT NULL,
    ALTER COLUMN blocked_ends_at SET NOT NULL;

-- Columnas de appointment_notifications.sql.
ALTER TABLE appointment
    ADD COLUMN IF NOT EXISTS confirmation_sent_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS reminder_sent_at TIMESTAMP;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'ex_appointment_no_overlap'
    ) THEN
        -- blocked_starts_at/blocked_ends_at ya existen y son NOT NULL en
        -- este punto (ver arriba), asi que esta es directamente la version
        -- definitiva del constraint (la misma que deja appointment_buffers.sql).
        ALTER TABLE appointment ADD CONSTRAINT ex_appointment_no_overlap
            EXCLUDE USING gist (
                id_calendar_profile WITH =,
                tstzrange(blocked_starts_at, blocked_ends_at, '[)') WITH &&
            ) WHERE (status IN ('pending_confirmation', 'confirmed'));
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_calendar_profile_owner ON calendar_profile (id_user, id_proyect) WHERE deletion_date IS NULL;
CREATE INDEX IF NOT EXISTS ix_appointment_type_profile ON appointment_type (id_calendar_profile) WHERE deletion_date IS NULL;
CREATE INDEX IF NOT EXISTS ix_availability_rule_profile_day ON availability_rule (id_calendar_profile, weekday) WHERE deletion_date IS NULL;
CREATE INDEX IF NOT EXISTS ix_availability_override_profile_date ON availability_override (id_calendar_profile, override_date) WHERE deletion_date IS NULL;
CREATE INDEX IF NOT EXISTS ix_appointment_project_start ON appointment (id_proyect, starts_at);

INSERT INTO entity_permission (
        id_permission, entity_name, control_type, menu_location, menu_group,
        menu_group_icon, menu_label, menu_order, created_by, creation_date, last_update_date
)
SELECT permission.id_permission, 'appointment', 15, 'sidebar', 'Operaciones',
            'calendar-days', 'Calendario', 75, permission.created_by, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
FROM permission
WHERE permission.deletion_date IS NULL
    AND lower(permission.permission_description) IN ('supervisor', 'gerente')
ON CONFLICT (id_permission, entity_name) DO UPDATE SET
        control_type = EXCLUDED.control_type,
        menu_location = EXCLUDED.menu_location,
        menu_group = EXCLUDED.menu_group,
        menu_group_icon = EXCLUDED.menu_group_icon,
        menu_label = EXCLUDED.menu_label,
        menu_order = EXCLUDED.menu_order,
        deletion_date = NULL,
        last_update_date = CURRENT_TIMESTAMP;

COMMIT;
