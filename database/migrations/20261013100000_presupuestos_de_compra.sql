-- Presupuesto de compras por proyecto, autorizado por gerencia.
--
-- Todo es idempotente: las migraciones se reaplican completas en cada arranque.
CREATE TABLE IF NOT EXISTS purchase_budget (
    id_purchase_budget  SERIAL PRIMARY KEY,
    id_proyect          INTEGER NOT NULL UNIQUE REFERENCES proyect (id_proyect),
    amount              NUMERIC(14, 2) NOT NULL,
    currency            VARCHAR(3) NOT NULL DEFAULT 'MXN',
    note                VARCHAR(300),
    updated_by          INTEGER NOT NULL,
    creation_date       TIMESTAMP NOT NULL DEFAULT now(),
    last_update_date    TIMESTAMP NOT NULL DEFAULT now(),
    CONSTRAINT ck_purchase_budget_amount CHECK (amount >= 0)
);

CREATE TABLE IF NOT EXISTS purchase_budget_event (
    id_purchase_budget_event SERIAL PRIMARY KEY,
    id_proyect               INTEGER NOT NULL REFERENCES proyect (id_proyect),
    amount_before            NUMERIC(14, 2),
    amount_after             NUMERIC(14, 2) NOT NULL,
    note                     VARCHAR(300),
    created_by               INTEGER NOT NULL,
    creation_date            TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_purchase_budget_event_proyect
    ON purchase_budget_event (id_proyect);

ALTER TABLE purchase_order ADD COLUMN IF NOT EXISTS exceeds_budget BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE purchase_order ADD COLUMN IF NOT EXISTS budget_detail TEXT;
