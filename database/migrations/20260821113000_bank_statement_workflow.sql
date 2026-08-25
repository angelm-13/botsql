BEGIN;

ALTER TABLE bank_statement ADD COLUMN IF NOT EXISTS starting_balance NUMERIC(14,2);
ALTER TABLE bank_statement ADD COLUMN IF NOT EXISTS ending_balance NUMERIC(14,2);
ALTER TABLE bank_statement ADD COLUMN IF NOT EXISTS average_balance NUMERIC(14,2);
ALTER TABLE bank_statement ADD COLUMN IF NOT EXISTS parser_name VARCHAR(80);
ALTER TABLE bank_statement ADD COLUMN IF NOT EXISTS extraction_confidence NUMERIC(5,2);
ALTER TABLE bank_statement ADD COLUMN IF NOT EXISTS extraction_errors JSONB;
ALTER TABLE bank_statement ADD COLUMN IF NOT EXISTS reconciliation_data JSONB;

ALTER TABLE bank_statement_movement ADD COLUMN IF NOT EXISTS sequence_number INTEGER;
ALTER TABLE bank_statement_movement ADD COLUMN IF NOT EXISTS settlement_date DATE;
ALTER TABLE bank_statement_movement ADD COLUMN IF NOT EXISTS code VARCHAR(30);
ALTER TABLE bank_statement_movement ADD COLUMN IF NOT EXISTS reference VARCHAR(100);
ALTER TABLE bank_statement_movement ADD COLUMN IF NOT EXISTS order_number VARCHAR(100);
ALTER TABLE bank_statement_movement ADD COLUMN IF NOT EXISTS origin_bank VARCHAR(100);
ALTER TABLE bank_statement_movement ADD COLUMN IF NOT EXISTS origin_account VARCHAR(50);
ALTER TABLE bank_statement_movement ADD COLUMN IF NOT EXISTS beneficiary VARCHAR(200);
ALTER TABLE bank_statement_movement ADD COLUMN IF NOT EXISTS balance NUMERIC(14,2);
ALTER TABLE bank_statement_movement ADD COLUMN IF NOT EXISTS reconciliation_note VARCHAR(500);

CREATE UNIQUE INDEX IF NOT EXISTS uq_bank_statement_movement_row
    ON bank_statement_movement (id_bank_statement, sequence_number)
    WHERE sequence_number IS NOT NULL;

COMMIT;