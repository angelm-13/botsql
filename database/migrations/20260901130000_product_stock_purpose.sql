-- Para que sirve cada producto en el almacen.
--
-- El almacen guarda dos cosas distintas y el sistema no las distinguia:
--
--   * **mercancia**: se compra para venderse. Su salida natural es una factura
--     de venta, y su valor es el costo de lo que queda por vender.
--   * **uso interno**: herramienta, equipo, consumible de operacion. No se
--     vende nunca; sale para usarse, prestarse o consumirse.
--
-- Sin la distincion, una herramienta prestada y un producto vendido se veian
-- igual en el saldo, y no habia forma de sacar "que tenemos para vender" ni
-- "que herramienta anda fuera". Tampoco habia nada que impidiera facturar la
-- venta de un taladro de la empresa.
--
-- Por omision `mercancia`, que es como se ha usado el almacen hasta ahora: al
-- aplicar esta migracion ningun producto cambia de comportamiento.

BEGIN;

ALTER TABLE product
    ADD COLUMN IF NOT EXISTS stock_purpose varchar(20) NOT NULL DEFAULT 'mercancia';

ALTER TABLE product DROP CONSTRAINT IF EXISTS ck_product_stock_purpose;
ALTER TABLE product
    ADD CONSTRAINT ck_product_stock_purpose
    CHECK (stock_purpose IN ('mercancia', 'uso_interno'));

COMMENT ON COLUMN product.stock_purpose IS
    'mercancia: se compra para venderse. uso_interno: herramienta, equipo o consumible de la empresa; no se vende.';

-- Se consulta junto con el modo de rastreo: "que herramienta serializada de uso
-- interno tengo", que es la pregunta del responsable de almacen.
CREATE INDEX IF NOT EXISTS idx_product_purpose_tracking
    ON product (stock_purpose, tracking_mode);

COMMIT;
