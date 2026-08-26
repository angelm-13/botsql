BEGIN;

ALTER TABLE appointment
    ADD COLUMN IF NOT EXISTS confirmation_sent_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS reminder_sent_at TIMESTAMP;

COMMIT;