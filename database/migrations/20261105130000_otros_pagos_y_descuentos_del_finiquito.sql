-- Otros pagos y descuentos del finiquito (Excel de la contadora, 2026-11-05):
-- bonos o pagos pendientes que se suman (con o sin ISR) e Infonavit, Fonacot o
-- deudas que se restan. Se editan desde la baja con el permiso de
-- employee_termination; sin entrada propia en el Gestor ni resiembra.
-- Idempotente: se reaplica en cada arranque.
BEGIN;

CREATE TABLE IF NOT EXISTS employee_termination_line (
    id_employee_termination_line SERIAL PRIMARY KEY,
    id_employee_termination INTEGER NOT NULL REFERENCES employee_termination (id_employee_termination),
    line_kind VARCHAR(20) NOT NULL,
    description VARCHAR(120) NOT NULL,
    amount NUMERIC(12, 2) NOT NULL,
    taxable BOOLEAN NOT NULL DEFAULT true,
    created_by INTEGER NOT NULL DEFAULT 1,
    creation_date TIMESTAMP NOT NULL DEFAULT now(),
    last_update_date TIMESTAMP NOT NULL DEFAULT now(),
    deletion_date TIMESTAMP NULL
);

ALTER TABLE employee_termination_line DROP CONSTRAINT IF EXISTS ck_employee_termination_line_kind;
ALTER TABLE employee_termination_line ADD CONSTRAINT ck_employee_termination_line_kind
    CHECK (line_kind IN ('earning', 'deduction'));
ALTER TABLE employee_termination_line DROP CONSTRAINT IF EXISTS ck_employee_termination_line_amount;
ALTER TABLE employee_termination_line ADD CONSTRAINT ck_employee_termination_line_amount CHECK (amount > 0);

CREATE INDEX IF NOT EXISTS ix_employee_termination_line_baja
    ON employee_termination_line (id_employee_termination);

COMMIT;
