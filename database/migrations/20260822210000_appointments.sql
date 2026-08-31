BEGIN;

CREATE EXTENSION IF NOT EXISTS btree_gist;

CREATE TABLE calendar_profile (
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

CREATE TABLE appointment_type (
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

CREATE TABLE availability_rule (
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

CREATE TABLE availability_override (
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

CREATE TABLE appointment (
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

ALTER TABLE appointment ADD CONSTRAINT ex_appointment_no_overlap
    EXCLUDE USING gist (
        id_calendar_profile WITH =,
        tstzrange(starts_at, ends_at, '[)') WITH &&
    ) WHERE (status IN ('pending_confirmation', 'confirmed'));

CREATE INDEX ix_calendar_profile_owner ON calendar_profile (id_user, id_proyect) WHERE deletion_date IS NULL;
CREATE INDEX ix_appointment_type_profile ON appointment_type (id_calendar_profile) WHERE deletion_date IS NULL;
CREATE INDEX ix_availability_rule_profile_day ON availability_rule (id_calendar_profile, weekday) WHERE deletion_date IS NULL;
CREATE INDEX ix_availability_override_profile_date ON availability_override (id_calendar_profile, override_date) WHERE deletion_date IS NULL;
CREATE INDEX ix_appointment_project_start ON appointment (id_proyect, starts_at);

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