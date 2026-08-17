BEGIN;

CREATE TABLE IF NOT EXISTS stamping_operation (
    id_stamping_operation SERIAL PRIMARY KEY,
    id_invoice INTEGER NOT NULL REFERENCES invoice(id_invoice),
    id_proyect INTEGER NOT NULL REFERENCES proyect(id_proyect),
    idempotency_key VARCHAR(100) NOT NULL UNIQUE,
    provider VARCHAR(30) NOT NULL,
    status VARCHAR(30) NOT NULL CHECK (status IN ('processing', 'stamped', 'rejected', 'uncertain', 'cancelled')),
    provider_reference VARCHAR(100),
    response_metadata JSONB,
    error_code VARCHAR(100),
    created_by INTEGER NOT NULL,
    creation_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_update_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_stamping_operation_invoice
    ON stamping_operation (id_invoice, creation_date);

COMMIT;