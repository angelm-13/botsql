-- Cancelacion de CFDI y complemento de pago.
--
-- Dos capacidades que el SAT exige y que el sistema no tenia.
--
-- CANCELACION. No es un interruptor: se solicita al SAT con un motivo y de ahi
-- puede salir cancelado de inmediato o quedar en proceso, esperando hasta 72
-- horas a que el receptor acepte, para terminar cancelado o rechazado. Guardar
-- solo una bandera en la factura perderia ese intermedio, que es justo donde
-- hay que saber que paso. Se conserva cada intento, porque una solicitud
-- rechazada se puede volver a pedir con otro motivo.
--
-- COMPLEMENTO DE PAGO. Cuando el metodo de pago es "en parcialidades o
-- diferido", la factura no acredita el cobro: cada abono exige su propio
-- comprobante de tipo P. Ese comprobante va en ceros -SubTotal y Total valen
-- cero- porque el importe vive dentro del complemento, no en el cuerpo. De
-- cada abono se guarda el saldo anterior, lo pagado y el saldo insoluto, que
-- es el encadenamiento con el que se reconstruye el estado de cuenta.

BEGIN;

CREATE TABLE IF NOT EXISTS invoice_cancellation (
    id_invoice_cancellation SERIAL PRIMARY KEY,
    id_invoice INTEGER NOT NULL REFERENCES invoice (id_invoice),
    id_proyect INTEGER NOT NULL REFERENCES proyect (id_proyect),
    motive VARCHAR(2) NOT NULL,
    substitution_uuid VARCHAR(36),
    status VARCHAR(20) NOT NULL,
    provider VARCHAR(30) NOT NULL,
    provider_reference VARCHAR(100),
    acknowledgement VARCHAR(64),
    response_metadata JSON,
    error_code VARCHAR(100),
    reason VARCHAR(300),
    idempotency_key VARCHAR(100) NOT NULL,
    created_by INTEGER NOT NULL,
    creation_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_update_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_date TIMESTAMP,
    CONSTRAINT uq_invoice_cancellation_idempotency_key UNIQUE (idempotency_key),
    CONSTRAINT ck_invoice_cancellation_motive CHECK (motive IN ('01', '02', '03', '04')),
    -- El motivo 01 es el unico que sustituye un comprobante por otro; los
    -- demas no admiten folio de sustitucion.
    CONSTRAINT ck_invoice_cancellation_substitution CHECK (
        (motive = '01' AND substitution_uuid IS NOT NULL)
        OR (motive <> '01' AND substitution_uuid IS NULL)
    )
);

CREATE INDEX IF NOT EXISTS ix_invoice_cancellation_invoice
    ON invoice_cancellation (id_invoice, creation_date);
CREATE INDEX IF NOT EXISTS ix_invoice_cancellation_status
    ON invoice_cancellation (status);

CREATE TABLE IF NOT EXISTS invoice_payment (
    id_invoice_payment SERIAL PRIMARY KEY,
    id_invoice INTEGER NOT NULL REFERENCES invoice (id_invoice),
    id_proyect INTEGER NOT NULL REFERENCES proyect (id_proyect),
    id_payment_invoice INTEGER REFERENCES invoice (id_invoice),
    paid_at TIMESTAMP NOT NULL,
    payment_form VARCHAR(2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'MXN',
    exchange_rate NUMERIC(18, 6) NOT NULL DEFAULT 1,
    instalment INTEGER NOT NULL,
    previous_balance NUMERIC(18, 2) NOT NULL,
    amount NUMERIC(18, 2) NOT NULL,
    outstanding_balance NUMERIC(18, 2) NOT NULL,
    operation_number VARCHAR(100),
    note VARCHAR(300),
    status VARCHAR(20) NOT NULL DEFAULT 'pendiente',
    stamp_metadata JSON,
    idempotency_key VARCHAR(100) NOT NULL,
    created_by INTEGER NOT NULL,
    creation_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_update_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deletion_date TIMESTAMP,
    CONSTRAINT uq_invoice_payment_idempotency_key UNIQUE (idempotency_key),
    -- Una parcialidad no se registra dos veces para la misma factura.
    CONSTRAINT uq_invoice_payment_instalment UNIQUE (id_invoice, instalment),
    CONSTRAINT ck_invoice_payment_amount_positive CHECK (amount > 0),
    CONSTRAINT ck_invoice_payment_previous_balance CHECK (previous_balance >= 0),
    CONSTRAINT ck_invoice_payment_outstanding CHECK (outstanding_balance >= 0)
);

CREATE INDEX IF NOT EXISTS ix_invoice_payment_invoice
    ON invoice_payment (id_invoice, instalment);

COMMIT;
