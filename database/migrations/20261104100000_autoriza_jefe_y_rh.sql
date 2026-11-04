-- Vacaciones, permisos y horas extra los autoriza el jefe directo y despues RH
-- (decision de RH, 2026-11-04).
--
-- employee_leave   estado nuevo boss_approved (la aprobo su jefe, falta RH) y el
--                  primer paso aparte: boss_reviewed_by, boss_reviewed_at,
--                  boss_review_note. reviewed_* sigue siendo el paso que la cierra.
-- overtime         approval_status: pending_hr (la registro el jefe), approved
--                  (RH la confirmo o la registro RH) o rejected. Solo approved se
--                  paga. Lo que ya existia queda approved: no cambia ninguna
--                  nomina calculada.
--
-- Reaplicable: ADD COLUMN IF NOT EXISTS y la restriccion se quita y se pone de
-- nuevo con la lista completa. La 20261022100000 solo la agrega si no existe, asi
-- que ya no la angosta.
BEGIN;

ALTER TABLE employee_leave
    ADD COLUMN IF NOT EXISTS boss_reviewed_by INTEGER NULL,
    ADD COLUMN IF NOT EXISTS boss_reviewed_at TIMESTAMP NULL,
    ADD COLUMN IF NOT EXISTS boss_review_note VARCHAR(300) NULL;
ALTER TABLE employee_leave DROP CONSTRAINT IF EXISTS ck_employee_leave_status;
ALTER TABLE employee_leave ADD CONSTRAINT ck_employee_leave_status
    CHECK (leave_status IN ('requested', 'boss_approved', 'approved', 'rejected', 'cancelled'));

ALTER TABLE overtime ADD COLUMN IF NOT EXISTS approval_status VARCHAR(20) NOT NULL DEFAULT 'approved';
ALTER TABLE overtime DROP CONSTRAINT IF EXISTS ck_overtime_approval;
ALTER TABLE overtime ADD CONSTRAINT ck_overtime_approval
    CHECK (approval_status IN ('pending_hr', 'approved', 'rejected'));

COMMIT;
