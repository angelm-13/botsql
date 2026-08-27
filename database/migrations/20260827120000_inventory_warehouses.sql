-- Almacenes en el inventario, construidos sobre las ubicaciones que ya existen.
--
-- Problema que resuelve: hoy un producto solo puede tener existencia en un
-- lugar (product.id_location con un solo product.cantidad), y el libro de
-- movimientos no registra donde ocurrio nada. Con eso es imposible saber que
-- hay en cada almacen ni mover mercancia entre ellos.
--
-- Decisiones:
--
-- 1) El almacen no es una tabla nueva: es una ubicacion cuyo tipo esta marcado
--    como almacen. Asi la jerarquia almacen -> zona -> rack -> posicion usa el
--    arbol de ubicaciones que el modulo ya tenia previsto, en lugar de agregar
--    un tercer concepto de almacen junto a location y logistics_warehouse.
--
-- 2) La auto-referencia de location pasa a ser llave foranea real. Estaba
--    declarada como un entero suelto, asi que admitia apuntar a una ubicacion
--    inexistente.
--
-- 3) inventory_stock guarda la existencia por producto y ubicacion. La
--    columna product.cantidad se conserva como el total del producto, que el
--    servicio mantiene como la suma de sus ubicaciones, para no romper lo que
--    ya la lee.
--
-- 4) El libro de movimientos gana la ubicacion donde ocurrio el movimiento y
--    el saldo de esa ubicacion. `balance_after` conserva su significado (el
--    total del producto) para que los renglones ya escritos sigan siendo
--    validos.

BEGIN;

-- 1) Que tipos de ubicacion son almacen -------------------------------------
ALTER TABLE location_type
    ADD COLUMN IF NOT EXISTS is_warehouse BOOLEAN NOT NULL DEFAULT FALSE;

COMMENT ON COLUMN location_type.is_warehouse IS
    'Las ubicaciones de este tipo son almacenes: la raiz del arbol de ubicaciones.';

-- 2) La jerarquia de ubicaciones, con integridad real -----------------------
-- Se limpian primero las referencias que apuntan a ubicaciones inexistentes,
-- porque sin llave foranea pudieron quedar huerfanas.
UPDATE location
SET id_location_reference = NULL
WHERE id_location_reference IS NOT NULL
  AND id_location_reference NOT IN (SELECT id_location FROM location);

-- Una ubicacion no puede ser su propio padre.
UPDATE location
SET id_location_reference = NULL
WHERE id_location_reference = id_location;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_location_parent'
    ) THEN
        ALTER TABLE location
            ADD CONSTRAINT fk_location_parent
            FOREIGN KEY (id_location_reference) REFERENCES location (id_location);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'ck_location_not_self_parent'
    ) THEN
        ALTER TABLE location
            ADD CONSTRAINT ck_location_not_self_parent
            CHECK (id_location_reference IS NULL OR id_location_reference <> id_location);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_location_parent ON location (id_location_reference);

-- 3) Existencia por producto y ubicacion ------------------------------------
CREATE TABLE IF NOT EXISTS inventory_stock (
    id_inventory_stock SERIAL PRIMARY KEY,
    id_product INTEGER NOT NULL REFERENCES product (id_product),
    id_location INTEGER NOT NULL REFERENCES location (id_location),
    quantity INTEGER NOT NULL DEFAULT 0,
    created_by INTEGER NOT NULL,
    creation_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_update_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_inventory_stock_product_location UNIQUE (id_product, id_location),
    CONSTRAINT ck_inventory_stock_quantity_non_negative CHECK (quantity >= 0)
);

CREATE INDEX IF NOT EXISTS ix_inventory_stock_location ON inventory_stock (id_location);

COMMENT ON TABLE inventory_stock IS
    'Existencia de un producto en una ubicacion. La suma por producto es product.cantidad.';

-- 4) El libro de movimientos registra donde ---------------------------------
ALTER TABLE inventory_ledger
    ADD COLUMN IF NOT EXISTS id_location INTEGER REFERENCES location (id_location),
    ADD COLUMN IF NOT EXISTS id_location_target INTEGER REFERENCES location (id_location),
    ADD COLUMN IF NOT EXISTS location_balance_after INTEGER,
    ADD COLUMN IF NOT EXISTS transfer_group VARCHAR(36);

COMMENT ON COLUMN inventory_ledger.id_location IS
    'Ubicacion donde ocurrio el movimiento.';
COMMENT ON COLUMN inventory_ledger.id_location_target IS
    'Solo en traspasos: la ubicacion contraria del par de renglones.';
COMMENT ON COLUMN inventory_ledger.location_balance_after IS
    'Saldo de esa ubicacion despues del movimiento. balance_after sigue siendo el total del producto.';
COMMENT ON COLUMN inventory_ledger.transfer_group IS
    'Une los dos renglones de un traspaso (salida y entrada).';

CREATE INDEX IF NOT EXISTS ix_inventory_ledger_location
    ON inventory_ledger (id_location, creation_date);
CREATE INDEX IF NOT EXISTS ix_inventory_ledger_transfer_group
    ON inventory_ledger (transfer_group);

-- 5) Se siembra la existencia actual en la ubicacion del producto -----------
-- Antes de esto la existencia vivia solo en product.cantidad; se traslada a
-- inventory_stock para que el punto de partida cuadre con el libro.
INSERT INTO inventory_stock (id_product, id_location, quantity, created_by)
SELECT p.id_product, p.id_location, COALESCE(p.cantidad, 0), COALESCE(p.created_by, 1)
FROM product p
WHERE p.deletion_date IS NULL
ON CONFLICT (id_product, id_location) DO NOTHING;

-- Los movimientos ya escritos ocurrieron en la ubicacion del producto.
UPDATE inventory_ledger l
SET id_location = p.id_location
FROM product p
WHERE l.id_product = p.id_product AND l.id_location IS NULL;

COMMIT;
