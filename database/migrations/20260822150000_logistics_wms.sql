CREATE TABLE IF NOT EXISTS logistics_warehouse (
    id_logistics_warehouse SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL UNIQUE,
    address VARCHAR(300),
    capacity NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK (capacity >= 0),
    status VARCHAR(20) NOT NULL DEFAULT 'activo' CHECK (status IN ('activo', 'inactivo')),
    created_by INTEGER NOT NULL REFERENCES "user"(id_user),
    creation_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_update_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deletion_date TIMESTAMP
);

CREATE TABLE IF NOT EXISTS logistics_location (
    id_logistics_location SERIAL PRIMARY KEY,
    id_logistics_warehouse INTEGER NOT NULL REFERENCES logistics_warehouse(id_logistics_warehouse),
    code VARCHAR(80) NOT NULL,
    zone VARCHAR(80),
    location_type VARCHAR(80),
    capacity NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK (capacity >= 0),
    status VARCHAR(20) NOT NULL DEFAULT 'activo' CHECK (status IN ('activo', 'inactivo')),
    created_by INTEGER NOT NULL REFERENCES "user"(id_user),
    creation_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_update_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deletion_date TIMESTAMP,
    CONSTRAINT uq_logistics_location_warehouse_code UNIQUE (id_logistics_warehouse, code)
);

CREATE TABLE IF NOT EXISTS logistics_inventory (
    id_logistics_inventory SERIAL PRIMARY KEY,
    id_customer_supplier INTEGER NOT NULL REFERENCES customer_supplier(id_customer_supplier),
    id_logistics_location INTEGER NOT NULL REFERENCES logistics_location(id_logistics_location),
    sku VARCHAR(100) NOT NULL,
    description VARCHAR(300),
    quantity NUMERIC(14,3) NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    lot VARCHAR(100),
    serial_number VARCHAR(120),
    status VARCHAR(30) NOT NULL DEFAULT 'activo'
        CHECK (status IN ('activo', 'pendiente_surtido', 'surtido', 'inactivo')),
    created_by INTEGER NOT NULL REFERENCES "user"(id_user),
    creation_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_update_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deletion_date TIMESTAMP
);

CREATE TABLE IF NOT EXISTS logistics_rack (
    id_logistics_rack SERIAL PRIMARY KEY,
    id_customer_supplier INTEGER NOT NULL REFERENCES customer_supplier(id_customer_supplier),
    id_logistics_location INTEGER NOT NULL REFERENCES logistics_location(id_logistics_location),
    code VARCHAR(100) NOT NULL UNIQUE,
    status VARCHAR(30) NOT NULL DEFAULT 'en_cliente'
        CHECK (status IN ('en_cliente', 'en_almacen', 'pendiente_retorno', 'en_reparacion')),
    condition VARCHAR(20) NOT NULL DEFAULT 'bueno' CHECK (condition IN ('bueno', 'regular', 'dañado')),
    quantity INTEGER NOT NULL DEFAULT 1 CHECK (quantity >= 0),
    sent_at DATE,
    received_at DATE,
    created_by INTEGER NOT NULL REFERENCES "user"(id_user),
    creation_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_update_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deletion_date TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_logistics_warehouse_status
    ON logistics_warehouse(status) WHERE deletion_date IS NULL;
CREATE INDEX IF NOT EXISTS ix_logistics_location_warehouse
    ON logistics_location(id_logistics_warehouse) WHERE deletion_date IS NULL;
CREATE INDEX IF NOT EXISTS ix_logistics_location_status
    ON logistics_location(status, zone) WHERE deletion_date IS NULL;
CREATE INDEX IF NOT EXISTS ix_logistics_inventory_client
    ON logistics_inventory(id_customer_supplier) WHERE deletion_date IS NULL;
CREATE INDEX IF NOT EXISTS ix_logistics_inventory_location
    ON logistics_inventory(id_logistics_location) WHERE deletion_date IS NULL;
CREATE INDEX IF NOT EXISTS ix_logistics_inventory_sku
    ON logistics_inventory(sku) WHERE deletion_date IS NULL;
CREATE INDEX IF NOT EXISTS ix_logistics_rack_client
    ON logistics_rack(id_customer_supplier) WHERE deletion_date IS NULL;
CREATE INDEX IF NOT EXISTS ix_logistics_rack_location
    ON logistics_rack(id_logistics_location) WHERE deletion_date IS NULL;
CREATE INDEX IF NOT EXISTS ix_logistics_rack_status
    ON logistics_rack(status, condition) WHERE deletion_date IS NULL;

INSERT INTO field (table_name, field_name, created_by, creation_date, last_update_date)
SELECT source_column.table_name, source_column.column_name, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
FROM information_schema.columns source_column
WHERE source_column.table_schema = 'public'
  AND source_column.table_name IN ('logistics_warehouse', 'logistics_location', 'logistics_inventory', 'logistics_rack')
  AND NOT EXISTS (
      SELECT 1 FROM field
      WHERE field.table_name = source_column.table_name
        AND field.field_name = source_column.column_name
  );

INSERT INTO entity_permission (
    id_permission, entity_name, control_type, menu_location, menu_group,
    menu_group_icon, menu_label, menu_order, created_by, creation_date, last_update_date
)
SELECT source_permission.id_permission, logistics_entity.entity_name,
       source_permission.control_type, 'sidebar', 'Logística', 'truck',
       logistics_entity.menu_label, logistics_entity.menu_order,
       1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
FROM entity_permission source_permission
CROSS JOIN (VALUES
    ('logistics_warehouse', 'Almacenes', 130),
    ('logistics_location', 'Ubicaciones', 140),
    ('logistics_inventory', 'Inventario', 150),
    ('logistics_rack', 'Racks', 160)
) AS logistics_entity(entity_name, menu_label, menu_order)
WHERE source_permission.entity_name = 'customer_supplier'
  AND source_permission.deletion_date IS NULL
ON CONFLICT (id_permission, entity_name) DO UPDATE SET
    control_type = EXCLUDED.control_type,
    menu_location = EXCLUDED.menu_location,
    menu_group = EXCLUDED.menu_group,
    menu_group_icon = EXCLUDED.menu_group_icon,
    menu_label = EXCLUDED.menu_label,
    menu_order = EXCLUDED.menu_order,
    deletion_date = NULL,
    last_update_date = CURRENT_TIMESTAMP;

INSERT INTO nm_field_permission (
    id_field, id_permission, control_type, created_by, creation_date, last_update_date
)
SELECT logistics_field.id_field, logistics_permission.id_permission, '15',
       1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
FROM field logistics_field
JOIN entity_permission logistics_permission
  ON logistics_permission.entity_name = logistics_field.table_name
WHERE logistics_field.table_name IN ('logistics_warehouse', 'logistics_location', 'logistics_inventory', 'logistics_rack')
  AND logistics_permission.deletion_date IS NULL
  AND NOT EXISTS (
      SELECT 1 FROM nm_field_permission existing
      WHERE existing.id_field = logistics_field.id_field
        AND existing.id_permission = logistics_permission.id_permission
        AND existing.deletion_date IS NULL
  );