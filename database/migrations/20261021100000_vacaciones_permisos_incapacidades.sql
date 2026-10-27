-- Vacaciones, permisos e incapacidades (ausencias justificadas).
--
-- De que se parte
-- ---------------
-- Con los horarios (20261020100000), un dia laboral sin checada es falta y no
-- se paga. Pero si el empleado estaba de vacaciones, con permiso o incapacitado,
-- el sistema no lo sabia y tambien lo contaba como falta.
--
-- Que se agrega
-- -------------
-- employee_leave   una ausencia justificada de un empleado, de una fecha a otra:
--   vacation       vacaciones: no es falta, se paga y se descuenta del saldo
--                  (LFT art. 76; solo cuentan los dias laborables de su horario).
--   paid_leave     permiso con goce: no es falta y se paga.
--   unpaid_leave   permiso sin goce: no es falta; sus dias laborables no se pagan.
--   disability     incapacidad del IMSS: no es falta y no se paga ningun dia del
--                  rango (el IMSS cubre el subsidio por dias naturales).
-- payroll_detail   dias de cada tipo en el periodo, para la pantalla y el recibo.
--
-- Las reglas viven en services/attendance_rules.py (que dia es falta y cual se
-- paga) y en services/employee_leave_service.py (saldo, que no se enciman, que
-- no caigan en un periodo cerrado). Decisiones de RH del 2026-10-21: no hay
-- vacaciones antes del primer año, los dias no usados no se acumulan y no se
-- registra ni edita una ausencia dentro de un periodo cerrado.
--
-- Reaplicable: CREATE ... IF NOT EXISTS y ADD COLUMN IF NOT EXISTS. No toca
-- entity_permission (los permisos llegan por la resiembra 20261021100100).
BEGIN;

CREATE TABLE IF NOT EXISTS employee_leave (
    id_employee_leave SERIAL PRIMARY KEY,
    id_user INTEGER NOT NULL REFERENCES "user"(id_user) DEFERRABLE INITIALLY DEFERRED,
    leave_type VARCHAR(20) NOT NULL
        CONSTRAINT ck_employee_leave_type CHECK (leave_type IN ('vacation', 'paid_leave', 'unpaid_leave', 'disability')),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    notes VARCHAR(300) NULL,
    created_by INTEGER NOT NULL DEFAULT 1,
    creation_date TIMESTAMP NOT NULL DEFAULT now(),
    last_update_date TIMESTAMP NOT NULL DEFAULT now(),
    deletion_date TIMESTAMP NULL,
    CONSTRAINT ck_employee_leave_dates CHECK (end_date >= start_date)
);
CREATE INDEX IF NOT EXISTS ix_employee_leave_user ON employee_leave (id_user);

ALTER TABLE payroll_detail
    ADD COLUMN IF NOT EXISTS vacation_days INTEGER NULL,
    ADD COLUMN IF NOT EXISTS paid_leave_days INTEGER NULL,
    ADD COLUMN IF NOT EXISTS unpaid_leave_days INTEGER NULL,
    ADD COLUMN IF NOT EXISTS disability_days INTEGER NULL;

COMMIT;
