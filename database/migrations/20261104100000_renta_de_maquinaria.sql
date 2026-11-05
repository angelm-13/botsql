-- Renta de maquinaria por proyecto (pedido de Adser, 2026-11-04).
--
-- La obra pide la maquinaria en su lista de necesidades (`need_kind = 'rental'`, con
-- el periodo en que la ocupa) y Compras la cubre con una orden, en un renglon de
-- renta (`line_kind = 'rental'`): tarifa por dia/semana/mes, llegada a obra,
-- prorroga y devolucion al proveedor. No toca permisos ni el Gestor.
--
-- Idempotente (se reaplica en cada arranque): columnas con ADD COLUMN IF NOT EXISTS
-- y restricciones con DROP IF EXISTS + ADD. Las filas existentes quedan como
-- 'material' / 'purchase' sin periodo, que es lo que las restricciones piden.
BEGIN;

ALTER TABLE proyect_material_need
    ADD COLUMN IF NOT EXISTS need_kind VARCHAR(10) NOT NULL DEFAULT 'material',
    ADD COLUMN IF NOT EXISTS rental_start DATE,
    ADD COLUMN IF NOT EXISTS rental_end DATE;

ALTER TABLE proyect_material_need DROP CONSTRAINT IF EXISTS ck_proyect_material_need_kind;
ALTER TABLE proyect_material_need ADD CONSTRAINT ck_proyect_material_need_kind
    CHECK (need_kind IN ('material', 'rental'));

ALTER TABLE proyect_material_need DROP CONSTRAINT IF EXISTS ck_proyect_material_need_rental_period;
ALTER TABLE proyect_material_need ADD CONSTRAINT ck_proyect_material_need_rental_period CHECK (
    (need_kind = 'rental' AND rental_start IS NOT NULL AND rental_end IS NOT NULL
     AND rental_end >= rental_start)
    OR (need_kind = 'material' AND rental_start IS NULL AND rental_end IS NULL));

ALTER TABLE purchase_order_line
    ADD COLUMN IF NOT EXISTS line_kind VARCHAR(10) NOT NULL DEFAULT 'purchase',
    ADD COLUMN IF NOT EXISTS rental_start DATE,
    ADD COLUMN IF NOT EXISTS rental_end DATE,
    ADD COLUMN IF NOT EXISTS rental_rate NUMERIC(14, 4),
    ADD COLUMN IF NOT EXISTS rental_rate_unit VARCHAR(10),
    ADD COLUMN IF NOT EXISTS rental_arrived_date DATE,
    ADD COLUMN IF NOT EXISTS rental_arrived_by INTEGER,
    ADD COLUMN IF NOT EXISTS rental_returned_date DATE,
    ADD COLUMN IF NOT EXISTS rental_returned_by INTEGER,
    ADD COLUMN IF NOT EXISTS rental_return_note VARCHAR(300),
    ADD COLUMN IF NOT EXISTS rental_extension_end DATE,
    ADD COLUMN IF NOT EXISTS rental_extension_note VARCHAR(300),
    ADD COLUMN IF NOT EXISTS rental_extension_by INTEGER,
    ADD COLUMN IF NOT EXISTS rental_reminder_date DATE;

ALTER TABLE purchase_order_line DROP CONSTRAINT IF EXISTS ck_purchase_order_line_kind;
ALTER TABLE purchase_order_line ADD CONSTRAINT ck_purchase_order_line_kind
    CHECK (line_kind IN ('purchase', 'rental'));

ALTER TABLE purchase_order_line DROP CONSTRAINT IF EXISTS ck_purchase_order_line_rental_period;
ALTER TABLE purchase_order_line ADD CONSTRAINT ck_purchase_order_line_rental_period CHECK (
    (line_kind = 'rental' AND rental_start IS NOT NULL AND rental_end IS NOT NULL
     AND rental_end >= rental_start)
    OR (line_kind = 'purchase' AND rental_start IS NULL));

ALTER TABLE purchase_order_line DROP CONSTRAINT IF EXISTS ck_purchase_order_line_rate_unit;
ALTER TABLE purchase_order_line ADD CONSTRAINT ck_purchase_order_line_rate_unit
    CHECK (rental_rate_unit IS NULL OR rental_rate_unit IN ('day', 'week', 'month'));

-- Las rentas que siguen en obra: la vista "Rentas activas" y el aviso de vencimiento.
CREATE INDEX IF NOT EXISTS ix_purchase_order_line_rental_open
    ON purchase_order_line (rental_end)
    WHERE line_kind = 'rental' AND rental_returned_date IS NULL AND deletion_date IS NULL;

COMMIT;
