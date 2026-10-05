-- `nm_incident_product.overdue_notified_date`: cuando se avisó por última vez
-- (campanita de notificaciones) que este renglón ya debió volver y no ha
-- vuelto. Sin esta marca, el job periódico que revisa vales vencidos
-- (`app/jobs/tasks_warehouse.py`) repetiría la misma notificación cada vez
-- que corre -- es el mismo patrón de deduplicación que ya usa
-- `appointment.reminder_sent_at` en `tasks_appointments.py`.
--
-- Se reaplica en cada arranque del pod (sin tabla de control, ver
-- ARQUITECTURA_TYAKXA_TNY.md 7.1): `ADD COLUMN IF NOT EXISTS` no hace nada la
-- segunda vez que ya existe.
BEGIN;

ALTER TABLE nm_incident_product
    ADD COLUMN IF NOT EXISTS overdue_notified_date TIMESTAMP;

COMMIT;
