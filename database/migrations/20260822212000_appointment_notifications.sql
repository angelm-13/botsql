BEGIN;

ALTER TABLE appointment
    ADD COLUMN confirmation_sent_at TIMESTAMP,
    ADD COLUMN reminder_sent_at TIMESTAMP;

COMMIT;