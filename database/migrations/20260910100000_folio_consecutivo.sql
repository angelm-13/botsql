BEGIN;

-- Folio consecutivo por empresa emisora (multiemisor). Solo se asigna al
-- timbrar cuando nadie capturo un folio propio -ver stamping.py:
-- next_folio_if_missing-. El contador arranca en el mayor folio numerico ya
-- usado por ese emisor + 1, nunca en 1 a ciegas, para no chocar con folios
-- capturados a mano antes de que existiera este contador.
CREATE TABLE IF NOT EXISTS invoice_folio_counter (
    id_customer_supplier INTEGER PRIMARY KEY REFERENCES customer_supplier (id_customer_supplier),
    next_folio INTEGER NOT NULL DEFAULT 1,
    last_update_date TIMESTAMP NOT NULL DEFAULT now()
);

COMMIT;
