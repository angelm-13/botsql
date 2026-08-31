BEGIN;

ALTER TABLE appointment
    ADD COLUMN IF NOT EXISTS blocked_starts_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS blocked_ends_at TIMESTAMPTZ;

-- Solo backfillea filas recien agregadas (columna aun en NULL); en una
-- corrida repetida ya son NOT NULL y el WHERE no matchea nada, así que no
-- pisa un blocked_starts_at/ends_at que la aplicación ya haya divergido de
-- starts_at/ends_at.
UPDATE appointment
SET blocked_starts_at = starts_at,
    blocked_ends_at = ends_at
WHERE blocked_starts_at IS NULL;

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