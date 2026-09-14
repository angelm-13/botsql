BEGIN;

CREATE TABLE IF NOT EXISTS restaurant_waiter (
    id_restaurant_waiter SERIAL PRIMARY KEY,
    id_proyect INTEGER NOT NULL REFERENCES proyect(id_proyect),
    id_user INTEGER REFERENCES "user"(id_user),
    name VARCHAR(120) NOT NULL,
    nickname VARCHAR(80) NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'active',
    max_tables INTEGER NOT NULL DEFAULT 15,
    created_by INTEGER NOT NULL REFERENCES "user"(id_user),
    creation_date TIMESTAMP NOT NULL DEFAULT now(),
    last_update_date TIMESTAMP NOT NULL DEFAULT now(),
    deletion_date TIMESTAMP
);

CREATE TABLE IF NOT EXISTS restaurant_table (
    id_restaurant_table SERIAL PRIMARY KEY,
    id_proyect INTEGER NOT NULL REFERENCES proyect(id_proyect),
    number INTEGER NOT NULL,
    capacity INTEGER NOT NULL DEFAULT 4,
    location_description VARCHAR(160),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_by INTEGER NOT NULL REFERENCES "user"(id_user),
    creation_date TIMESTAMP NOT NULL DEFAULT now(),
    last_update_date TIMESTAMP NOT NULL DEFAULT now(),
    deletion_date TIMESTAMP,
    CONSTRAINT uq_restaurant_table_project_number UNIQUE (id_proyect, number)
);

CREATE TABLE IF NOT EXISTS restaurant_guisado (
    id_restaurant_guisado SERIAL PRIMARY KEY,
    id_proyect INTEGER NOT NULL REFERENCES proyect(id_proyect),
    name VARCHAR(120) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_by INTEGER NOT NULL REFERENCES "user"(id_user),
    creation_date TIMESTAMP NOT NULL DEFAULT now(),
    last_update_date TIMESTAMP NOT NULL DEFAULT now(),
    deletion_date TIMESTAMP
);

CREATE TABLE IF NOT EXISTS restaurant_dish (
    id_restaurant_dish SERIAL PRIMARY KEY,
    id_proyect INTEGER NOT NULL REFERENCES proyect(id_proyect),
    title VARCHAR(140) NOT NULL,
    description TEXT,
    icon VARCHAR(40) NOT NULL DEFAULT 'plate',
    category VARCHAR(30) NOT NULL DEFAULT 'taco',
    price NUMERIC(10, 2) NOT NULL DEFAULT 0,
    production_cost NUMERIC(10, 2) NOT NULL DEFAULT 0,
    requires_guisado BOOLEAN NOT NULL DEFAULT FALSE,
    schedule VARCHAR(10) NOT NULL DEFAULT 'all',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_by INTEGER NOT NULL REFERENCES "user"(id_user),
    creation_date TIMESTAMP NOT NULL DEFAULT now(),
    last_update_date TIMESTAMP NOT NULL DEFAULT now(),
    deletion_date TIMESTAMP
);

CREATE TABLE IF NOT EXISTS restaurant_visit (
    id_restaurant_visit SERIAL PRIMARY KEY,
    id_proyect INTEGER NOT NULL REFERENCES proyect(id_proyect),
    id_restaurant_table INTEGER NOT NULL REFERENCES restaurant_table(id_restaurant_table),
    id_restaurant_waiter INTEGER REFERENCES restaurant_waiter(id_restaurant_waiter),
    diners_count INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    opened_at TIMESTAMP NOT NULL DEFAULT now(),
    closed_at TIMESTAMP,
    created_by INTEGER NOT NULL REFERENCES "user"(id_user),
    creation_date TIMESTAMP NOT NULL DEFAULT now(),
    last_update_date TIMESTAMP NOT NULL DEFAULT now(),
    deletion_date TIMESTAMP
);

CREATE TABLE IF NOT EXISTS restaurant_order (
    id_restaurant_order SERIAL PRIMARY KEY,
    id_proyect INTEGER NOT NULL REFERENCES proyect(id_proyect),
    id_restaurant_visit INTEGER NOT NULL REFERENCES restaurant_visit(id_restaurant_visit),
    diner_index INTEGER NOT NULL DEFAULT 1,
    id_restaurant_waiter INTEGER REFERENCES restaurant_waiter(id_restaurant_waiter),
    status VARCHAR(40) NOT NULL DEFAULT 'borrador',
    tip_type VARCHAR(20),
    tip_percent NUMERIC(5, 2),
    tip_amount NUMERIC(10, 2) NOT NULL DEFAULT 0,
    started_at TIMESTAMP NOT NULL DEFAULT now(),
    sent_at TIMESTAMP,
    cooked_at TIMESTAMP,
    ready_at TIMESTAMP,
    delivered_at TIMESTAMP,
    paid_at TIMESTAMP,
    created_by INTEGER NOT NULL REFERENCES "user"(id_user),
    creation_date TIMESTAMP NOT NULL DEFAULT now(),
    last_update_date TIMESTAMP NOT NULL DEFAULT now(),
    deletion_date TIMESTAMP
);

CREATE TABLE IF NOT EXISTS restaurant_order_item (
    id_restaurant_order_item SERIAL PRIMARY KEY,
    id_restaurant_order INTEGER NOT NULL REFERENCES restaurant_order(id_restaurant_order),
    id_restaurant_dish INTEGER NOT NULL REFERENCES restaurant_dish(id_restaurant_dish),
    quantity INTEGER NOT NULL DEFAULT 1,
    unit_price NUMERIC(10, 2) NOT NULL DEFAULT 0,
    note VARCHAR(255),
    id_guisado_1 INTEGER REFERENCES restaurant_guisado(id_restaurant_guisado),
    id_guisado_2 INTEGER REFERENCES restaurant_guisado(id_restaurant_guisado),
    combinado BOOLEAN NOT NULL DEFAULT FALSE,
    created_by INTEGER NOT NULL REFERENCES "user"(id_user),
    creation_date TIMESTAMP NOT NULL DEFAULT now(),
    last_update_date TIMESTAMP NOT NULL DEFAULT now(),
    deletion_date TIMESTAMP
);

CREATE TABLE IF NOT EXISTS restaurant_reservation (
    id_restaurant_reservation SERIAL PRIMARY KEY,
    id_proyect INTEGER NOT NULL REFERENCES proyect(id_proyect),
    id_restaurant_table INTEGER REFERENCES restaurant_table(id_restaurant_table),
    name VARCHAR(140) NOT NULL,
    reservation_date DATE NOT NULL,
    reservation_time TIME NOT NULL,
    guests INTEGER NOT NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'pending',
    event_type VARCHAR(80),
    created_by INTEGER NOT NULL REFERENCES "user"(id_user),
    creation_date TIMESTAMP NOT NULL DEFAULT now(),
    last_update_date TIMESTAMP NOT NULL DEFAULT now(),
    deletion_date TIMESTAMP
);

CREATE TABLE IF NOT EXISTS restaurant_inventory_item (
    id_restaurant_inventory_item SERIAL PRIMARY KEY,
    id_proyect INTEGER NOT NULL REFERENCES proyect(id_proyect),
    description VARCHAR(160) NOT NULL,
    quantity NUMERIC(12, 3) NOT NULL DEFAULT 0,
    unit VARCHAR(40) NOT NULL,
    cost_per_unit NUMERIC(10, 2) NOT NULL DEFAULT 0,
    created_by INTEGER NOT NULL REFERENCES "user"(id_user),
    creation_date TIMESTAMP NOT NULL DEFAULT now(),
    last_update_date TIMESTAMP NOT NULL DEFAULT now(),
    deletion_date TIMESTAMP
);

CREATE TABLE IF NOT EXISTS restaurant_recipe_item (
    id_restaurant_recipe_item SERIAL PRIMARY KEY,
    id_proyect INTEGER NOT NULL REFERENCES proyect(id_proyect),
    id_restaurant_dish INTEGER NOT NULL REFERENCES restaurant_dish(id_restaurant_dish),
    id_restaurant_inventory_item INTEGER NOT NULL REFERENCES restaurant_inventory_item(id_restaurant_inventory_item),
    quantity NUMERIC(12, 3) NOT NULL,
    unit VARCHAR(40) NOT NULL,
    created_by INTEGER NOT NULL REFERENCES "user"(id_user),
    creation_date TIMESTAMP NOT NULL DEFAULT now(),
    last_update_date TIMESTAMP NOT NULL DEFAULT now(),
    deletion_date TIMESTAMP
);

CREATE TABLE IF NOT EXISTS restaurant_cash_session (
    id_restaurant_cash_session SERIAL PRIMARY KEY,
    id_proyect INTEGER NOT NULL REFERENCES proyect(id_proyect),
    opened_by_id INTEGER NOT NULL REFERENCES "user"(id_user),
    opened_at TIMESTAMP NOT NULL DEFAULT now(),
    opening_amount NUMERIC(10, 2) NOT NULL DEFAULT 0,
    closed_by_id INTEGER REFERENCES "user"(id_user),
    closed_at TIMESTAMP,
    closing_amount NUMERIC(10, 2),
    expected_amount NUMERIC(10, 2),
    difference NUMERIC(10, 2),
    notes VARCHAR(255),
    status VARCHAR(20) NOT NULL DEFAULT 'open',
    created_by INTEGER NOT NULL REFERENCES "user"(id_user),
    creation_date TIMESTAMP NOT NULL DEFAULT now(),
    last_update_date TIMESTAMP NOT NULL DEFAULT now(),
    deletion_date TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_restaurant_waiter_id_proyect ON restaurant_waiter(id_proyect);
CREATE INDEX IF NOT EXISTS ix_restaurant_table_id_proyect ON restaurant_table(id_proyect);
CREATE INDEX IF NOT EXISTS ix_restaurant_guisado_id_proyect ON restaurant_guisado(id_proyect);
CREATE INDEX IF NOT EXISTS ix_restaurant_dish_id_proyect ON restaurant_dish(id_proyect);
CREATE INDEX IF NOT EXISTS ix_restaurant_visit_id_proyect ON restaurant_visit(id_proyect);
CREATE INDEX IF NOT EXISTS ix_restaurant_visit_status ON restaurant_visit(status);
CREATE INDEX IF NOT EXISTS ix_restaurant_order_id_proyect ON restaurant_order(id_proyect);
CREATE INDEX IF NOT EXISTS ix_restaurant_order_id_restaurant_visit ON restaurant_order(id_restaurant_visit);
CREATE INDEX IF NOT EXISTS ix_restaurant_order_status ON restaurant_order(status);
CREATE INDEX IF NOT EXISTS ix_restaurant_order_item_id_restaurant_order ON restaurant_order_item(id_restaurant_order);
CREATE INDEX IF NOT EXISTS ix_restaurant_reservation_id_proyect ON restaurant_reservation(id_proyect);
CREATE INDEX IF NOT EXISTS ix_restaurant_inventory_item_id_proyect ON restaurant_inventory_item(id_proyect);
CREATE INDEX IF NOT EXISTS ix_restaurant_recipe_item_id_proyect ON restaurant_recipe_item(id_proyect);
CREATE INDEX IF NOT EXISTS ix_restaurant_cash_session_id_proyect ON restaurant_cash_session(id_proyect);
CREATE INDEX IF NOT EXISTS ix_restaurant_cash_session_status ON restaurant_cash_session(status);

COMMIT;