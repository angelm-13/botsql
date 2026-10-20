-- La clase de un articulo: herramienta, consumible, sobrante o recargable (2026-10-20).
--
-- Una etiqueta para clasificar y filtrar lo que hay en el almacen y lo que se compra.
-- Va en tres lugares: el MATERIAL (catalogo) la trae por omision, el PRODUCTO la hereda
-- y puede cambiarla, y el RENGLON de la orden de compra la lleva hasta el producto al
-- recibir. No cambia el rastreo (`tracking_mode`) ni si se vende (`stock_purpose`).
--
-- Nullable: lo que ya existe no tiene clase y no se le puede inventar una; se captura
-- cuando alguien lo edite. Idempotente: toda migracion se reaplica en cada arranque.
BEGIN;

ALTER TABLE material ADD COLUMN IF NOT EXISTS item_class varchar(20);
ALTER TABLE product ADD COLUMN IF NOT EXISTS item_class varchar(20);
ALTER TABLE purchase_order_line ADD COLUMN IF NOT EXISTS item_class varchar(20);

ALTER TABLE material DROP CONSTRAINT IF EXISTS ck_material_item_class;
ALTER TABLE material ADD CONSTRAINT ck_material_item_class
    CHECK (item_class IS NULL OR item_class IN ('herramienta', 'consumible', 'sobrante', 'recargable'));
ALTER TABLE product DROP CONSTRAINT IF EXISTS ck_product_item_class;
ALTER TABLE product ADD CONSTRAINT ck_product_item_class
    CHECK (item_class IS NULL OR item_class IN ('herramienta', 'consumible', 'sobrante', 'recargable'));
ALTER TABLE purchase_order_line DROP CONSTRAINT IF EXISTS ck_purchase_order_line_item_class;
ALTER TABLE purchase_order_line ADD CONSTRAINT ck_purchase_order_line_item_class
    CHECK (item_class IS NULL OR item_class IN ('herramienta', 'consumible', 'sobrante', 'recargable'));

CREATE INDEX IF NOT EXISTS idx_product_item_class ON product (item_class);

COMMIT;
