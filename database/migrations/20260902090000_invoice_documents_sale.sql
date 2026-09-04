-- Una partida de factura o causa un movimiento, o documenta uno que ya ocurrio.
--
-- El problema
-- -----------
-- Una venta de mostrador ya descuenta del almacen cuando se cobra. Si despues
-- se factura y la factura tambien descuenta, el producto sale dos veces del
-- inventario por haberse vendido una. El saldo queda mal y nada avisa: las dos
-- operaciones son correctas por separado.
--
-- La regla
-- --------
-- Cada partida de factura hace una de dos cosas, nunca las dos:
--
--   * la CAUSA: una venta directa capturada en facturacion saca la mercancia;
--     una factura de compra la mete.
--   * la DOCUMENTA: la venta ya ocurrio en el punto de venta o en el
--     restaurante y ya movio el almacen; la factura solo la respalda ante el
--     SAT y no vuelve a tocar existencias.
--
-- Como se distingue
-- -----------------
-- `invoice.source_module` y `invoice.source_reference` dicen de que venta nace
-- la factura. Vacios significa que la factura es el origen y por lo tanto mueve.
-- Con valor, el movimiento ya esta en el libro y la factura lo documenta.
--
-- Se guarda en la factura y no se deduce al momento a proposito: la respuesta a
-- "esta factura movio inventario" no puede depender de lo que haya en el libro
-- cuando alguien pregunte. Si manana se borra o reclasifica un movimiento, la
-- factura seguira diciendo de que venta nacio.
--
-- El reference_type del libro
-- ---------------------------
-- El movimiento de una venta del punto de venta se venia guardando como
-- `reference_type = 'invoice'` con el folio del POS. Eso era falso: lo causo una
-- venta, no una factura, y ademas choca con el 'invoice' que si usa el nucleo.
-- Sin poder distinguirlos no hay forma de preguntar "esto ya lo movio una
-- venta", que es justo lo que esta regla necesita. Se reclasifica a 'sale'.

BEGIN;

ALTER TABLE invoice
  ADD COLUMN IF NOT EXISTS source_module VARCHAR(20),
  ADD COLUMN IF NOT EXISTS source_reference VARCHAR(80);

COMMENT ON COLUMN invoice.source_module IS
  'De que modulo viene la venta que esta factura documenta: pos, restaurante, logistica. Vacio = la factura es el origen del movimiento y por lo tanto mueve inventario.';
COMMENT ON COLUMN invoice.source_reference IS
  'Folio o identificador de la venta en su modulo de origen. Con esto se llega a los movimientos que la venta ya escribio.';

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'ck_invoice_source_module'
  ) THEN
    ALTER TABLE invoice ADD CONSTRAINT ck_invoice_source_module
      CHECK (source_module IS NULL
             OR source_module IN ('pos', 'restaurante', 'logistica'));
  END IF;

  -- Un modulo de origen sin referencia no sirve para nada: no se podria llegar
  -- a los movimientos que documenta.
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'ck_invoice_source_pair'
  ) THEN
    ALTER TABLE invoice ADD CONSTRAINT ck_invoice_source_pair
      CHECK ((source_module IS NULL AND source_reference IS NULL)
             OR (source_module IS NOT NULL AND source_reference IS NOT NULL));
  END IF;
END $$;

-- Para llegar de la venta a su factura sin recorrer la tabla entera.
CREATE INDEX IF NOT EXISTS idx_invoice_source
  ON invoice (source_module, source_reference)
  WHERE source_module IS NOT NULL;

-- Los movimientos causados por una venta de mostrador se reclasifican. Se
-- acota a source_module = 'pos' para no tocar el 'invoice' legitimo del nucleo.
UPDATE inventory_ledger
   SET reference_type = 'sale'
 WHERE source_module = 'pos'
   AND reference_type = 'invoice';

COMMIT;
