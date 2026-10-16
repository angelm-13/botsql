-- Estados del periodo de nomina y dias trabajados en el detalle.
--
-- De que se parte
-- ---------------
-- El calculo de nomina (payroll_calculation_service.py) se podia repetir para
-- siempre, aun despues de pagado el periodo, y los detalles y movimientos de un
-- periodo pagado se podian editar o borrar. Tampoco quedaba guardado cuantos
-- dias trabajo cada empleado: se calculaba y se perdia, y el recibo lo necesita.
--
-- Que se agrega
-- -------------
-- payroll_period.period_state   'open' (recien creado), 'calculated' (ya se
--                                calculo) o 'closed' (pagado: congelado).
--                                Es una columna propia, como proyect_status, y
--                                no una fila del catalogo generico `status`,
--                                que cada cliente llena distinto. `id_status`
--                                no se toca.
-- payroll_period.closed_at / closed_by       quien y cuando lo cerro.
-- payroll_period.reopened_at / reopened_by   quien y cuando lo reabrio por
--                                            ultima vez (solo administracion).
-- payroll_detail.days_worked    dias con checada que uso el calculo.
--
-- Reaplicable: ADD COLUMN IF NOT EXISTS y el CHECK solo se crea si no existe
-- (reescribir un CHECK en cada arranque ya trono en otras migraciones). No toca
-- entity_permission.
BEGIN;

ALTER TABLE payroll_period
    ADD COLUMN IF NOT EXISTS period_state VARCHAR(20) NOT NULL DEFAULT 'open',
    ADD COLUMN IF NOT EXISTS closed_at TIMESTAMP NULL,
    ADD COLUMN IF NOT EXISTS closed_by INTEGER NULL,
    ADD COLUMN IF NOT EXISTS reopened_at TIMESTAMP NULL,
    ADD COLUMN IF NOT EXISTS reopened_by INTEGER NULL;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_payroll_period_state') THEN
        ALTER TABLE payroll_period
            ADD CONSTRAINT ck_payroll_period_state
            CHECK (period_state IN ('open', 'calculated', 'closed'));
    END IF;
END
$$;

ALTER TABLE payroll_detail
    ADD COLUMN IF NOT EXISTS days_worked INTEGER NULL;

COMMIT;
