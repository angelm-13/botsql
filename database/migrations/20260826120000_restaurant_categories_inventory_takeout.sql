-- Extiende el modulo de restaurante con lo que le faltaba frente al
-- proyecto de referencia (demo_restaurante), sin tocar facturacion: esa
-- vive en el modulo de facturacion del core, no aqui.
--
--   1. restaurant_category            catalogo de categorias del menu
--   2. restaurant_inventory_movement  ledger de existencias
--   3. restaurant_visit               ordenes para llevar (sin mesa)
--
-- La auditoria administrativa reusa la tabla audit_log del core, por lo que
-- no se crea ninguna tabla de bitacora propia del restaurante.

BEGIN;

-- 1. Categorias del menu ----------------------------------------------------
-- restaurant_dish.category sigue guardando el slug como texto; esta tabla es
-- el catalogo que lo valida y le da nombre/icono/orden. No se migran los
-- platillos existentes: mientras un proyecto no defina categorias, el
-- servicio sigue aceptando el set fijo que ya usaba.
CREATE TABLE IF NOT EXISTS restaurant_category (
    id_restaurant_category SERIAL PRIMARY KEY,
    id_proyect INTEGER NOT NULL REFERENCES proyect(id_proyect),
    slug VARCHAR(30) NOT NULL,
    label VARCHAR(80) NOT NULL,
    icon VARCHAR(40) NOT NULL DEFAULT 'plate',
    color VARCHAR(20),
    sort_order INTEGER NOT NULL DEFAULT 100,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_by INTEGER NOT NULL REFERENCES "user"(id_user),
    creation_date TIMESTAMP NOT NULL DEFAULT now(),
    last_update_date TIMESTAMP NOT NULL DEFAULT now(),
    deletion_date TIMESTAMP,
    CONSTRAINT uq_restaurant_category_project_slug UNIQUE (id_proyect, slug)
);

CREATE INDEX IF NOT EXISTS ix_restaurant_category_proyect
    ON restaurant_category (id_proyect);

-- 2. Ledger de existencias --------------------------------------------------
-- Antes restaurant_inventory_item.quantity se sobrescribia sin rastro. Cada
-- renglon guarda el saldo antes y despues, para que el saldo actual sea
-- verificable contra el historial.
CREATE TABLE IF NOT EXISTS restaurant_inventory_movement (
    id_restaurant_inventory_movement SERIAL PRIMARY KEY,
    id_proyect INTEGER NOT NULL REFERENCES proyect(id_proyect),
    id_restaurant_inventory_item INTEGER NOT NULL
        REFERENCES restaurant_inventory_item(id_restaurant_inventory_item),
    movement_type VARCHAR(20) NOT NULL,
    quantity NUMERIC(12, 3) NOT NULL,
    previous_quantity NUMERIC(12, 3) NOT NULL,
    new_quantity NUMERIC(12, 3) NOT NULL,
    unit_cost NUMERIC(10, 2),
    reason VARCHAR(255),
    created_by INTEGER NOT NULL REFERENCES "user"(id_user),
    creation_date TIMESTAMP NOT NULL DEFAULT now(),
    last_update_date TIMESTAMP NOT NULL DEFAULT now(),
    deletion_date TIMESTAMP,
    CONSTRAINT ck_restaurant_inventory_movement_type
        CHECK (movement_type IN ('entrada', 'salida', 'merma', 'ajuste')),
    -- El saldo resultante nunca puede quedar negativo: un consumo mayor al
    -- disponible es un error de captura, no un sobregiro valido.
    CONSTRAINT ck_restaurant_inventory_movement_new_quantity
        CHECK (new_quantity >= 0)
);

CREATE INDEX IF NOT EXISTS ix_restaurant_inventory_movement_item
    ON restaurant_inventory_movement (id_restaurant_inventory_item, creation_date);
CREATE INDEX IF NOT EXISTS ix_restaurant_inventory_movement_proyect
    ON restaurant_inventory_movement (id_proyect);

-- 3. Ordenes para llevar ----------------------------------------------------
-- Una orden para llevar no ocupa mesa, asi que id_restaurant_table pasa a ser
-- opcional. service_type distingue los dos casos y daily_number/service_date
-- dan el folio visible al cliente ("para llevar #7"), que reinicia cada dia
-- por proyecto.
ALTER TABLE restaurant_visit
    ALTER COLUMN id_restaurant_table DROP NOT NULL;

ALTER TABLE restaurant_visit
    ADD COLUMN IF NOT EXISTS service_type VARCHAR(20) NOT NULL DEFAULT 'mesa',
    ADD COLUMN IF NOT EXISTS customer_name VARCHAR(140),
    ADD COLUMN IF NOT EXISTS daily_number INTEGER,
    ADD COLUMN IF NOT EXISTS service_date DATE;

-- Coherencia entre el tipo de servicio y las columnas que le corresponden:
-- una visita de mesa exige mesa; una para llevar exige folio y fecha.
ALTER TABLE restaurant_visit
    DROP CONSTRAINT IF EXISTS ck_restaurant_visit_service_type;
ALTER TABLE restaurant_visit
    ADD CONSTRAINT ck_restaurant_visit_service_type CHECK (
        (service_type = 'mesa' AND id_restaurant_table IS NOT NULL)
        OR (service_type = 'para_llevar'
            AND daily_number IS NOT NULL
            AND service_date IS NOT NULL)
    );

CREATE INDEX IF NOT EXISTS ix_restaurant_visit_service_type
    ON restaurant_visit (service_type);

-- El folio es unico por proyecto y dia; sin esto dos cajas simultaneas
-- podrian emitir el mismo numero al cliente.
CREATE UNIQUE INDEX IF NOT EXISTS uq_restaurant_visit_daily_number
    ON restaurant_visit (id_proyect, service_date, daily_number)
    WHERE service_type = 'para_llevar' AND deletion_date IS NULL;

COMMIT;
