-- Forma de salario por empleado: por dia, por hora o fijo por periodo
-- (decisiones de RH, 2026-10-30).
--
-- De que se parte
-- ---------------
-- El calculo solo conocia el salario diario (`user.base_salary`). Muchas
-- empresas pagan por hora o un sueldo fijo por semana, catorcena, quincena o
-- mes, y de eso depende tambien el precio de la hora extra.
--
-- Que se agrega
-- -------------
-- employee_salary   como gana cada empleado y desde/hasta cuando (guarda el
--                   historial de aumentos): salary_type daily, hourly o fixed;
--                   amount; fixed_frequency (weekly, biweekly, semimonthly,
--                   monthly) solo si es fijo. Quien no tiene forma capturada
--                   sigue con base_salary como diario (services/salary_service.py).
--
-- Reaplicable: CREATE ... IF NOT EXISTS. No toca entity_permission (los permisos
-- llegan por la resiembra 20261030190000).
BEGIN;

CREATE TABLE IF NOT EXISTS employee_salary (
    id_employee_salary SERIAL PRIMARY KEY,
    id_user INTEGER NOT NULL REFERENCES "user"(id_user) DEFERRABLE INITIALLY DEFERRED,
    salary_type VARCHAR(20) NOT NULL
        CONSTRAINT ck_employee_salary_type CHECK (salary_type IN ('daily', 'hourly', 'fixed')),
    amount NUMERIC(12, 2) NOT NULL CONSTRAINT ck_employee_salary_amount CHECK (amount > 0),
    fixed_frequency VARCHAR(20) NULL
        CONSTRAINT ck_employee_salary_frequency CHECK (fixed_frequency IS NULL
            OR fixed_frequency IN ('weekly', 'biweekly', 'semimonthly', 'monthly')),
    valid_from DATE NOT NULL,
    valid_to DATE NULL,
    created_by INTEGER NOT NULL DEFAULT 1,
    creation_date TIMESTAMP NOT NULL DEFAULT now(),
    last_update_date TIMESTAMP NOT NULL DEFAULT now(),
    deletion_date TIMESTAMP NULL,
    CONSTRAINT ck_employee_salary_dates CHECK (valid_to IS NULL OR valid_to >= valid_from)
);
CREATE INDEX IF NOT EXISTS ix_employee_salary_user ON employee_salary (id_user);

COMMIT;
