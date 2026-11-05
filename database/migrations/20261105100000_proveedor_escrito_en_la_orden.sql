-- El proveedor de una orden de compra se escribe a mano (pedido de Adser via Alan,
-- 2026-11-05): dar de alta a cada proveedor en Clientes y proveedores antes de
-- comprar les resultaba engorroso.
--
-- `purchase_order.supplier_name` guarda el nombre tal como se escribio. Si coincide
-- con un proveedor dado de alta, la orden queda ademas ligada a el
-- (`id_customer_supplier`) y se sigue comparando el RFC de la factura; si no, la
-- orden lleva solo el nombre. Por eso `id_customer_supplier` deja de ser obligatorio
-- en la orden y en sus comprobantes.
--
-- Idempotente (se reaplica en cada arranque): ADD COLUMN IF NOT EXISTS, DROP NOT NULL
-- (no falla si ya se quito) y el relleno solo toca filas sin nombre.
BEGIN;

ALTER TABLE purchase_order ADD COLUMN IF NOT EXISTS supplier_name VARCHAR(200);
ALTER TABLE purchase_order ALTER COLUMN id_customer_supplier DROP NOT NULL;
ALTER TABLE purchase_voucher ALTER COLUMN id_customer_supplier DROP NOT NULL;

-- Las ordenes que ya existen toman el nombre del proveedor con el que se armaron.
UPDATE purchase_order po
   SET supplier_name = cs.name
  FROM customer_supplier cs
 WHERE cs.id_customer_supplier = po.id_customer_supplier
   AND po.supplier_name IS NULL;

COMMIT;
