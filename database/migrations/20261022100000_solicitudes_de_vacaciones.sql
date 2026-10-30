-- Solicitudes de vacaciones y permisos: el empleado pide y su jefe (o RH) autoriza.
--
-- De que se parte
-- ---------------
-- `employee_leave` (20261021100000) solo la capturaba RH y toda ausencia contaba
-- de inmediato. Ahora el propio empleado puede pedir vacaciones o un permiso, y
-- su supervisor (`user.supervisor`) o RH lo aprueba o lo rechaza.
--
-- Que se agrega a employee_leave
-- ------------------------------
-- leave_status   requested (pedida), approved (aprobada), rejected (rechazada)
--                o cancelled (cancelada por el empleado). Solo lo aprobado
--                cuenta para la nomina, las incidencias y como ausencia; lo
--                pedido aparta dias del saldo de vacaciones.
-- requested_by   quien la pidio (nulo si la registro RH directamente).
-- reviewed_by, reviewed_at, review_note   quien la reviso, cuando y su nota.
--
-- Lo ya registrado queda como aprobado (DEFAULT 'approved'), igual que funcionaba.
-- Decisiones de RH (2026-10-22): el empleado pide vacaciones y permisos (la
-- incapacidad la registra RH); autoriza su supervisor o RH; lo pedido aparta dias.
--
-- Reaplicable: ADD COLUMN IF NOT EXISTS y el CHECK con guarda. No toca
-- entity_permission (el catalogo de campos llega por la resiembra 20261022100100).
BEGIN;

ALTER TABLE employee_leave
    ADD COLUMN IF NOT EXISTS leave_status VARCHAR(20) NOT NULL DEFAULT 'approved',
    ADD COLUMN IF NOT EXISTS requested_by INTEGER NULL,
    ADD COLUMN IF NOT EXISTS reviewed_by INTEGER NULL,
    ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMP NULL,
    ADD COLUMN IF NOT EXISTS review_note VARCHAR(300) NULL;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_employee_leave_status') THEN
        ALTER TABLE employee_leave ADD CONSTRAINT ck_employee_leave_status
            CHECK (leave_status IN ('requested', 'approved', 'rejected', 'cancelled'));
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_employee_leave_status ON employee_leave (leave_status);

COMMIT;
