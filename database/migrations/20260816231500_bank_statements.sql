BEGIN;

ALTER TABLE bank_account ADD COLUMN IF NOT EXISTS id_proyect INTEGER REFERENCES proyect(id_proyect);

CREATE TABLE IF NOT EXISTS bank_statement (
    id_bank_statement SERIAL PRIMARY KEY, id_bank_account INTEGER NOT NULL REFERENCES bank_account(id_bank_account),
    id_proyect INTEGER NOT NULL REFERENCES proyect(id_proyect), file_hash VARCHAR(64) NOT NULL UNIQUE,
    original_filename VARCHAR(255) NOT NULL, period_start DATE, period_end DATE,
    total_debits NUMERIC(14,2) NOT NULL, total_credits NUMERIC(14,2) NOT NULL,
    status VARCHAR(30) NOT NULL, created_by INTEGER NOT NULL, creation_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS bank_statement_movement (
    id_bank_statement_movement SERIAL PRIMARY KEY, id_bank_statement INTEGER NOT NULL REFERENCES bank_statement(id_bank_statement),
    movement_date DATE NOT NULL, description VARCHAR(500) NOT NULL, debit NUMERIC(14,2) NOT NULL DEFAULT 0,
    credit NUMERIC(14,2) NOT NULL DEFAULT 0, id_invoice INTEGER REFERENCES invoice(id_invoice),
    CHECK ((debit > 0 AND credit = 0) OR (credit > 0 AND debit = 0))
);
CREATE INDEX IF NOT EXISTS ix_bank_statement_movement_statement ON bank_statement_movement (id_bank_statement);

COMMIT;