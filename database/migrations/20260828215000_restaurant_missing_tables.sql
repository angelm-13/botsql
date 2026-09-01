BEGIN;

-- Dos tablas del modulo restaurante tienen modelo (backend/app/models/restaurant.py)
-- e indice de created_by (20260828220000_indices_llaves_foraneas.sql) desde que
-- se agregaron, pero nunca tuvieron su CREATE TABLE: se quedaron fuera de
-- 20260817120000_restaurant_module.sql, que ya estaba aplicado cuando se
-- escribieron. Verificado en tyakxa-dev: la migracion de indices truena en la
-- primera (restaurant_category), y de nuevo en la segunda (restaurant_inventory_movement)
-- una vez agregada esta.

-- restaurant_dish.category se sigue guardando como texto libre; esta tabla es
-- solo el catalogo que lo valida y le da nombre, icono y orden de presentacion.
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

CREATE INDEX IF NOT EXISTS ix_restaurant_category_id_proyect ON restaurant_category(id_proyect);

-- Ledger de existencias de restaurant_inventory_item: cada alta, baja, merma o
-- ajuste queda como renglon en vez de sobrescribir la cantidad en sitio.
CREATE TABLE IF NOT EXISTS restaurant_inventory_movement (
    id_restaurant_inventory_movement SERIAL PRIMARY KEY,
    id_proyect INTEGER NOT NULL REFERENCES proyect(id_proyect),
    id_restaurant_inventory_item INTEGER NOT NULL REFERENCES restaurant_inventory_item(id_restaurant_inventory_item),
    movement_type VARCHAR(20) NOT NULL,
    quantity NUMERIC(12, 3) NOT NULL,
    previous_quantity NUMERIC(12, 3) NOT NULL,
    new_quantity NUMERIC(12, 3) NOT NULL,
    unit_cost NUMERIC(10, 2),
    reason VARCHAR(255),
    created_by INTEGER NOT NULL REFERENCES "user"(id_user),
    creation_date TIMESTAMP NOT NULL DEFAULT now(),
    last_update_date TIMESTAMP NOT NULL DEFAULT now(),
    deletion_date TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_restaurant_inventory_movement_id_proyect ON restaurant_inventory_movement(id_proyect);
CREATE INDEX IF NOT EXISTS ix_restaurant_inventory_movement_id_restaurant_inventory_item ON restaurant_inventory_movement(id_restaurant_inventory_item);

COMMIT;
