BEGIN;

CREATE TABLE IF NOT EXISTS quotation_comment (
    id_quotation_comment SERIAL PRIMARY KEY,
    id_invoice INTEGER NOT NULL REFERENCES invoice(id_invoice),
    id_user INTEGER NOT NULL REFERENCES "user"(id_user),
    message VARCHAR(1000) NOT NULL,
    creation_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_quotation_comment_id_invoice
    ON quotation_comment (id_invoice, creation_date);

COMMIT;