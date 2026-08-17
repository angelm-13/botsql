BEGIN;

CREATE TABLE IF NOT EXISTS inventory_ledger (
    id_inventory_ledger SERIAL PRIMARY KEY,
    id_product INTEGER NOT NULL REFERENCES product(id_product),
    id_proyect INTEGER NOT NULL REFERENCES proyect(id_proyect),
    movement_type VARCHAR(30) NOT NULL,
    quantity_delta INTEGER NOT NULL CHECK (quantity_delta <> 0),
    balance_after INTEGER NOT NULL CHECK (balance_after >= 0),
    idempotency_key VARCHAR(100) NOT NULL,
    reference_type VARCHAR(50),
    reference_id VARCHAR(100),
    reason VARCHAR(250),
    created_by INTEGER NOT NULL,
    creation_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_inventory_ledger_idempotency_key UNIQUE (idempotency_key)
);

CREATE INDEX IF NOT EXISTS ix_inventory_ledger_product_created
    ON inventory_ledger (id_product, creation_date);
CREATE INDEX IF NOT EXISTS ix_inventory_ledger_project_created
    ON inventory_ledger (id_proyect, creation_date);

COMMIT;