-- La orden de compra, con la evidencia de que se compro.
--
-- Una compra que solo se marca como "comprada" no demuestra nada. Aqui comprar es
-- registrar una orden con proveedor, folio, monto, forma de pago y comprobante; cada
-- paso -cotizar, autorizar, comprar, recibir- lo da una persona distinta y deja
-- renglon en `purchase_event`, que solo se agrega.
--
-- Una orden, varios proyectos: una compra real surte a varias obras. El comprobante
-- pertenece a UNA orden y los renglones reparten por proyecto. Lo que se prohibe es
-- usar el mismo comprobante en dos ordenes (contar el mismo dinero dos veces); los
-- tres indices unicos de abajo son la red de seguridad de esa regla, aparte de la
-- comprobacion del servicio: huella del archivo, folio por proveedor y UUID del CFDI.
--
-- `purchase_policy` es una sola fila con los montos de autorizacion, editable sin
-- tocar codigo. Nace en el modo mas estricto: toda orden se autoriza (`authorize_above`
-- = 0) y nadie compra por su cuenta (`manager_buys_above` vacio).
--
-- Se reaplica en cada arranque del pod (sin tabla de control): todo es IF NOT EXISTS
-- y la fila de la politica se inserta solo si no existe, asi que nunca pisa lo que
-- alguien ya configuro.
BEGIN;

CREATE TABLE IF NOT EXISTS purchase_order (
    id_purchase_order          SERIAL PRIMARY KEY,
    folio                      VARCHAR(30) NOT NULL UNIQUE,
    id_customer_supplier       INTEGER NOT NULL REFERENCES customer_supplier(id_customer_supplier),
    order_status               VARCHAR(24) NOT NULL DEFAULT 'draft',
    description                VARCHAR(300),
    expected_date              DATE,
    quoted_total               NUMERIC(14,2),
    authorized_total           NUMERIC(14,2),
    total_amount               NUMERIC(14,2),
    currency                   VARCHAR(3) NOT NULL DEFAULT 'MXN',
    requires_authorization     BOOLEAN NOT NULL DEFAULT TRUE,
    requires_manager_purchase  BOOLEAN NOT NULL DEFAULT FALSE,
    authorized_by              INTEGER,
    authorized_date            TIMESTAMP,
    authorization_note         VARCHAR(300),
    purchase_folio             VARCHAR(60),
    purchase_date              DATE,
    payment_method             VARCHAR(20),
    payment_reference          VARCHAR(80),
    paid_externally            BOOLEAN NOT NULL DEFAULT FALSE,
    purchased_by               INTEGER,
    purchased_date             TIMESTAMP,
    created_by                 INTEGER NOT NULL DEFAULT 1,
    creation_date              TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_update_date           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deletion_date              TIMESTAMP,
    CONSTRAINT ck_purchase_order_status CHECK (order_status IN
        ('draft', 'pending_authorization', 'authorized', 'rejected', 'purchased',
         'partially_received', 'received', 'closed', 'cancelled')),
    CONSTRAINT ck_purchase_order_payment_method CHECK (payment_method IS NULL OR
        payment_method IN ('cash', 'transfer', 'card', 'credit', 'check', 'other'))
);

CREATE INDEX IF NOT EXISTS idx_purchase_order_supplier
    ON purchase_order (id_customer_supplier) WHERE deletion_date IS NULL;
CREATE INDEX IF NOT EXISTS idx_purchase_order_status
    ON purchase_order (order_status) WHERE deletion_date IS NULL;

CREATE TABLE IF NOT EXISTS purchase_order_line (
    id_purchase_order_line     SERIAL PRIMARY KEY,
    id_purchase_order          INTEGER NOT NULL REFERENCES purchase_order(id_purchase_order),
    id_proyect_material_need   INTEGER REFERENCES proyect_material_need(id_proyect_material_need),
    id_proyect                 INTEGER REFERENCES proyect(id_proyect),
    id_material                INTEGER REFERENCES material(id_material),
    description                VARCHAR(200) NOT NULL,
    unit                       VARCHAR(40),
    quantity                   INTEGER NOT NULL,
    unit_cost                  NUMERIC(14,4),
    quantity_received          INTEGER NOT NULL DEFAULT 0,
    created_by                 INTEGER NOT NULL DEFAULT 1,
    creation_date              TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_update_date           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deletion_date              TIMESTAMP,
    CONSTRAINT ck_purchase_order_line_quantity CHECK (quantity > 0),
    CONSTRAINT ck_purchase_order_line_received CHECK (quantity_received >= 0)
);

CREATE INDEX IF NOT EXISTS idx_purchase_order_line_order
    ON purchase_order_line (id_purchase_order) WHERE deletion_date IS NULL;
CREATE INDEX IF NOT EXISTS idx_purchase_order_line_proyect
    ON purchase_order_line (id_proyect) WHERE deletion_date IS NULL;

CREATE TABLE IF NOT EXISTS purchase_voucher (
    id_purchase_voucher        SERIAL PRIMARY KEY,
    id_purchase_order          INTEGER NOT NULL REFERENCES purchase_order(id_purchase_order),
    id_customer_supplier       INTEGER NOT NULL,
    kind                       VARCHAR(14) NOT NULL,
    folio                      VARCHAR(60),
    amount                     NUMERIC(14,2),
    issue_date                 DATE,
    original_filename          VARCHAR(255) NOT NULL,
    extension                  VARCHAR(10) NOT NULL,
    mime_type                  VARCHAR(100) NOT NULL,
    file_size                  INTEGER NOT NULL,
    sha256                     VARCHAR(64) NOT NULL,
    file_path                  VARCHAR(500) NOT NULL DEFAULT '',
    cfdi_uuid                  VARCHAR(40),
    rfc_emisor                 VARCHAR(20),
    created_by                 INTEGER NOT NULL DEFAULT 1,
    creation_date              TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deletion_date              TIMESTAMP,
    CONSTRAINT ck_purchase_voucher_kind CHECK (kind IN
        ('quote', 'invoice', 'receipt', 'payment_proof'))
);

CREATE INDEX IF NOT EXISTS idx_purchase_voucher_order
    ON purchase_voucher (id_purchase_order) WHERE deletion_date IS NULL;
-- El mismo papel no justifica dos compras: tres llaves, tres indices, en TODA la base.
CREATE UNIQUE INDEX IF NOT EXISTS uq_purchase_voucher_sha256
    ON purchase_voucher (sha256) WHERE deletion_date IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_purchase_voucher_cfdi_uuid
    ON purchase_voucher (cfdi_uuid) WHERE deletion_date IS NULL AND cfdi_uuid IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_purchase_voucher_supplier_folio
    ON purchase_voucher (id_customer_supplier, upper(folio))
    WHERE deletion_date IS NULL AND folio IS NOT NULL AND kind IN ('invoice', 'receipt');

CREATE TABLE IF NOT EXISTS purchase_event (
    id_purchase_event          SERIAL PRIMARY KEY,
    id_purchase_order          INTEGER NOT NULL REFERENCES purchase_order(id_purchase_order),
    event_type                 VARCHAR(30) NOT NULL,
    from_status                VARCHAR(24),
    to_status                  VARCHAR(24),
    note                       VARCHAR(300),
    detail                     TEXT,
    created_by                 INTEGER NOT NULL,
    creation_date              TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_purchase_event_order
    ON purchase_event (id_purchase_order, id_purchase_event);

CREATE TABLE IF NOT EXISTS purchase_policy (
    id_purchase_policy         INTEGER PRIMARY KEY,
    authorize_above            NUMERIC(14,2) NOT NULL DEFAULT 0,
    manager_buys_above         NUMERIC(14,2),
    overrun_percent            NUMERIC(5,2) NOT NULL DEFAULT 10,
    updated_by                 INTEGER,
    last_update_date           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_purchase_policy_single CHECK (id_purchase_policy = 1),
    CONSTRAINT ck_purchase_policy_amounts CHECK (
        authorize_above >= 0 AND overrun_percent >= 0
        AND (manager_buys_above IS NULL OR manager_buys_above >= 0))
);

-- El modo mas estricto. Solo si no existe: nunca pisa lo que alguien ya configuro.
INSERT INTO purchase_policy (id_purchase_policy, authorize_above, manager_buys_above, overrun_percent)
SELECT 1, 0, NULL, 10
WHERE NOT EXISTS (SELECT 1 FROM purchase_policy WHERE id_purchase_policy = 1);

COMMIT;
