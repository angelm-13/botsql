CREATE TABLE IF NOT EXISTS logistics_address (
    id_logistics_address SERIAL PRIMARY KEY,
    id_customer_supplier INTEGER NOT NULL REFERENCES customer_supplier(id_customer_supplier),
    name VARCHAR(150) NOT NULL,
    address_line VARCHAR(250) NOT NULL,
    city VARCHAR(100),
    state VARCHAR(100),
    country VARCHAR(2) DEFAULT 'MX',
    postal_code VARCHAR(10),
    address_type VARCHAR(30) NOT NULL DEFAULT 'operativa',
    status VARCHAR(20) NOT NULL DEFAULT 'activo' CHECK (status IN ('activo', 'inactivo')),
    created_by INTEGER NOT NULL REFERENCES "user"(id_user),
    creation_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_update_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deletion_date TIMESTAMP
);

CREATE TABLE IF NOT EXISTS logistics_contract (
    id_logistics_contract SERIAL PRIMARY KEY,
    id_customer_supplier INTEGER NOT NULL REFERENCES customer_supplier(id_customer_supplier),
    contract_number VARCHAR(80) NOT NULL UNIQUE,
    start_date DATE NOT NULL,
    end_date DATE,
    sla_level VARCHAR(20) NOT NULL DEFAULT 'standard' CHECK (sla_level IN ('standard', 'premium')),
    status VARCHAR(20) NOT NULL DEFAULT 'activo' CHECK (status IN ('activo', 'inactivo')),
    created_by INTEGER NOT NULL REFERENCES "user"(id_user),
    creation_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_update_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deletion_date TIMESTAMP,
    CHECK (end_date IS NULL OR end_date >= start_date)
);

CREATE TABLE IF NOT EXISTS logistics_rate (
    id_logistics_rate SERIAL PRIMARY KEY,
    id_customer_supplier INTEGER NOT NULL REFERENCES customer_supplier(id_customer_supplier),
    service_type VARCHAR(100) NOT NULL,
    origin VARCHAR(150),
    destination VARCHAR(150),
    unit_type VARCHAR(80),
    amount NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK (amount >= 0),
    currency VARCHAR(3) NOT NULL DEFAULT 'MXN' CHECK (currency IN ('MXN', 'USD')),
    status VARCHAR(20) NOT NULL DEFAULT 'activo' CHECK (status IN ('activo', 'inactivo')),
    created_by INTEGER NOT NULL REFERENCES "user"(id_user),
    creation_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_update_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deletion_date TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_logistics_address_customer
    ON logistics_address(id_customer_supplier) WHERE deletion_date IS NULL;
CREATE INDEX IF NOT EXISTS ix_logistics_contract_customer
    ON logistics_contract(id_customer_supplier) WHERE deletion_date IS NULL;
CREATE INDEX IF NOT EXISTS ix_logistics_rate_customer
    ON logistics_rate(id_customer_supplier) WHERE deletion_date IS NULL;
CREATE INDEX IF NOT EXISTS ix_logistics_rate_route
    ON logistics_rate(origin, destination) WHERE deletion_date IS NULL;

INSERT INTO field (table_name, field_name, created_by, creation_date, last_update_date)
SELECT source_column.table_name, source_column.column_name, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
FROM information_schema.columns source_column
WHERE source_column.table_schema = 'public'
  AND source_column.table_name IN ('logistics_address', 'logistics_contract', 'logistics_rate')
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
    ('logistics_address', 'Direcciones', 30),
    ('logistics_contract', 'Contratos', 40),
    ('logistics_rate', 'Tarifas', 50)
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
WHERE logistics_field.table_name IN ('logistics_address', 'logistics_contract', 'logistics_rate')
  AND logistics_permission.deletion_date IS NULL
  AND NOT EXISTS (
      SELECT 1 FROM nm_field_permission existing
      WHERE existing.id_field = logistics_field.id_field
        AND existing.id_permission = logistics_permission.id_permission
        AND existing.deletion_date IS NULL
  );