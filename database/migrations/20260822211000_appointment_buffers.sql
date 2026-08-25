BEGIN;

ALTER TABLE appointment
    ADD COLUMN blocked_starts_at TIMESTAMPTZ,
    ADD COLUMN blocked_ends_at TIMESTAMPTZ;

UPDATE appointment
SET blocked_starts_at = starts_at,
    blocked_ends_at = ends_at;

ALTER TABLE appointment
    ALTER COLUMN blocked_starts_at SET NOT NULL,
    ALTER COLUMN blocked_ends_at SET NOT NULL,
    DROP CONSTRAINT ex_appointment_no_overlap;

ALTER TABLE appointment ADD CONSTRAINT ex_appointment_no_overlap
    EXCLUDE USING gist (
        id_calendar_profile WITH =,
        tstzrange(blocked_starts_at, blocked_ends_at, '[)') WITH &&
    ) WHERE (status IN ('pending_confirmation', 'confirmed'));

COMMIT;