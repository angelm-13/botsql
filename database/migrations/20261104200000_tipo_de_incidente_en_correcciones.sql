-- Tipo de incidente de cada correccion de checada (respuestas de RH, 2026-11-04):
-- olvido checar (forgot), fallo el checador (device_failure), comision o
-- diligencia (field_work) y permiso por horas (hourly_leave). Nula en las
-- correcciones anteriores. Idempotente: se reaplica en cada arranque.
BEGIN;

ALTER TABLE attendance_correction ADD COLUMN IF NOT EXISTS incident_kind VARCHAR(20);

ALTER TABLE attendance_correction DROP CONSTRAINT IF EXISTS ck_attendance_correction_incident_kind;
ALTER TABLE attendance_correction ADD CONSTRAINT ck_attendance_correction_incident_kind CHECK (
    incident_kind IS NULL OR incident_kind IN ('forgot', 'device_failure', 'field_work', 'hourly_leave')
);

COMMIT;
