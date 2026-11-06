-- Grupos de pago: semanal, catorcenal, quincenal o mensual por grupo de empleados.
--
-- De que se parte
-- ---------------
-- El periodo de nomina solo tenia fechas y el calculo adivinaba la tarifa del
-- ISR por cuantos dias duraba: la segunda quincena de febrero (13 dias) caia en
-- la tarifa diaria y una catorcena (14) en la quincenal. Tampoco habia forma de
-- pagar semanal a unos y quincenal a otros (revision contable, 2026-10-28).
--
-- Que se agrega
-- -------------
-- payroll_group            un grupo con nombre y periodicidad: weekly
--                          (semanal), biweekly (catorcenal), semimonthly
--                          (quincenal) o monthly (mensual). Uno solo marcado
--                          is_default: recibe a quien no tiene grupo asignado.
--                          Se siembra "General" (quincenal) como el de por omision.
-- employee_payroll_group   a que grupo pertenece cada empleado, con vigencia
--                          (valid_to nulo = sin fin). Guarda el historial.
-- payroll_period.id_payroll_group   de que grupo es el periodo. Los periodos que
--                          ya existen quedan sin grupo y calculan como siempre
--                          (todos los empleados, tarifa por dias).
--
-- Reaplicable: CREATE ... IF NOT EXISTS, ADD COLUMN IF NOT EXISTS, la llave
-- foranea con guarda y el grupo General solo si no hay ningun grupo por omision
-- (si RH marca otro, no se vuelve a crear). No toca entity_permission (los
-- permisos llegan por la resiembra 20261028190000).
BEGIN;

CREATE TABLE IF NOT EXISTS payroll_group (
    id_payroll_group SERIAL PRIMARY KEY,
    group_name VARCHAR(120) NOT NULL,
    pay_frequency VARCHAR(20) NOT NULL
        CONSTRAINT ck_payroll_group_frequency CHECK (pay_frequency IN ('weekly', 'biweekly', 'semimonthly', 'monthly')),
    is_default BOOLEAN NOT NULL DEFAULT false,
    created_by INTEGER NOT NULL DEFAULT 1,
    creation_date TIMESTAMP NOT NULL DEFAULT now(),
    last_update_date TIMESTAMP NOT NULL DEFAULT now(),
    deletion_date TIMESTAMP NULL
);

CREATE TABLE IF NOT EXISTS employee_payroll_group (
    id_employee_payroll_group SERIAL PRIMARY KEY,
    id_user INTEGER NOT NULL REFERENCES "user"(id_user) DEFERRABLE INITIALLY DEFERRED,
    id_payroll_group INTEGER NOT NULL REFERENCES payroll_group(id_payroll_group) DEFERRABLE INITIALLY DEFERRED,
    valid_from DATE NOT NULL,
    valid_to DATE NULL,
    created_by INTEGER NOT NULL DEFAULT 1,
    creation_date TIMESTAMP NOT NULL DEFAULT now(),
    last_update_date TIMESTAMP NOT NULL DEFAULT now(),
    deletion_date TIMESTAMP NULL,
    CONSTRAINT ck_employee_payroll_group_dates CHECK (valid_to IS NULL OR valid_to >= valid_from)
);
CREATE INDEX IF NOT EXISTS ix_employee_payroll_group_user ON employee_payroll_group (id_user);

ALTER TABLE payroll_period
    ADD COLUMN IF NOT EXISTS id_payroll_group INTEGER NULL;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_payroll_period_payroll_group') THEN
        ALTER TABLE payroll_period ADD CONSTRAINT fk_payroll_period_payroll_group
            FOREIGN KEY (id_payroll_group) REFERENCES payroll_group(id_payroll_group) DEFERRABLE INITIALLY DEFERRED;
    END IF;
END $$;

INSERT INTO payroll_group (group_name, pay_frequency, is_default)
SELECT 'General', 'semimonthly', true
WHERE NOT EXISTS (SELECT 1 FROM payroll_group WHERE is_default AND deletion_date IS NULL);

COMMIT;
