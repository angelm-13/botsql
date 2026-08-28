-- Comprobantes relacionados (CfdiRelacionados), base de las notas de credito.
--
-- Una nota de credito no es una factura negativa ni una cancelacion parcial:
-- es un CFDI de egreso, con importes en positivo, que declara con que factura
-- se relaciona y como. Ese "como" es el tipo de relacion, y no es un detalle
-- administrativo:
--
--   01  nota de credito por descuento o bonificacion. El cliente se queda con
--       la mercancia, asi que el almacen NO se toca.
--   03  devolucion de mercancia. El cliente la regresa, y entonces si vuelve
--       al almacen.
--
-- Confundirlas infla la existencia con producto que nunca regreso.
--
-- La tabla es generica a proposito: el mismo nodo lo usan la sustitucion al
-- cancelar (04) y la aplicacion de anticipos (07).

BEGIN;

CREATE TABLE IF NOT EXISTS cfdi_relation (
    id_cfdi_relation SERIAL PRIMARY KEY,
    -- El comprobante que declara la relacion; en una nota de credito, la nota.
    id_invoice INTEGER NOT NULL REFERENCES invoice (id_invoice),
    relation_type VARCHAR(2) NOT NULL,
    -- La referencia que viaja en el XML. Manda sobre id_related_invoice,
    -- porque el comprobante relacionado puede ser de otro emisor y no vivir
    -- en este sistema.
    related_uuid VARCHAR(36) NOT NULL,
    id_related_invoice INTEGER REFERENCES invoice (id_invoice),
    idempotency_key VARCHAR(100),
    created_by INTEGER NOT NULL,
    creation_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_cfdi_relation_invoice_type_uuid UNIQUE (id_invoice, relation_type, related_uuid),
    CONSTRAINT uq_cfdi_relation_idempotency_key UNIQUE (idempotency_key),
    CONSTRAINT ck_cfdi_relation_type CHECK (relation_type IN ('01','02','03','04','05','06','07'))
);

CREATE INDEX IF NOT EXISTS ix_cfdi_relation_related_uuid ON cfdi_relation (related_uuid);
CREATE INDEX IF NOT EXISTS ix_cfdi_relation_related_invoice ON cfdi_relation (id_related_invoice);

COMMIT;
