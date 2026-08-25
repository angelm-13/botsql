CREATE TABLE IF NOT EXISTS logistics_contact (
    id_logistics_contact SERIAL PRIMARY KEY,
    id_customer_supplier INTEGER NOT NULL REFERENCES customer_supplier(id_customer_supplier),
    full_name VARCHAR(150) NOT NULL,
    email VARCHAR(100),
    phone VARCHAR(30),
    position VARCHAR(80),
    status VARCHAR(20) NOT NULL DEFAULT 'activo' CHECK (status IN ('activo', 'inactivo')),
    created_by INTEGER NOT NULL REFERENCES "user"(id_user),
    creation_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_update_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deletion_date TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_logistics_contact_customer
    ON logistics_contact(id_customer_supplier) WHERE deletion_date IS NULL;

INSERT INTO field (table_name, field_name, created_by, creation_date, last_update_date)
SELECT 'logistics_contact', column_name, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
FROM information_schema.columns source_column
WHERE source_column.table_schema = 'public'
  AND source_column.table_name = 'logistics_contact'
  AND NOT EXISTS (
      SELECT 1 FROM field
      WHERE field.table_name = 'logistics_contact' AND field.field_name = source_column.column_name
  );

INSERT INTO entity_permission (
    id_permission, entity_name, control_type, menu_location, menu_group,
    menu_group_icon, menu_label, menu_order, created_by, creation_date, last_update_date
)
SELECT id_permission, 'logistics_contact', control_type, 'sidebar', 'Logística',
       'truck', 'Contactos', 20, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
FROM entity_permission source_permission
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
SELECT logistics_field.id_field, logistics_permission.id_permission, '15', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
FROM field logistics_field
JOIN entity_permission logistics_permission ON logistics_permission.entity_name = 'logistics_contact'
WHERE logistics_field.table_name = 'logistics_contact'
  AND logistics_permission.deletion_date IS NULL
  AND NOT EXISTS (
      SELECT 1 FROM nm_field_permission existing
      WHERE existing.id_field = logistics_field.id_field
        AND existing.id_permission = logistics_permission.id_permission
        AND existing.deletion_date IS NULL
  );