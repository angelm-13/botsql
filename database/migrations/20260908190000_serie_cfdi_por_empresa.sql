BEGIN;

-- Serie de CFDI por defecto de la empresa (opcional, igual que "Serie del
-- CFDI" en Mi Empresa de cotizador_demo). Sin esto, una factura manual nunca
-- llevaba Serie salvo que alguien la escribiera a mano por factura.
ALTER TABLE customer_supplier ADD COLUMN IF NOT EXISTS serie_csd VARCHAR(25);

COMMIT;
