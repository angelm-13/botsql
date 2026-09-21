CREATE TABLE IF NOT EXISTS logistics_branch (
    id_logistics_branch SERIAL PRIMARY KEY,
    name VARCHAR(180) NOT NULL,
    postal_code VARCHAR(20),
    series VARCHAR(30),
    address TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'activo' CHECK (status IN ('activo', 'inactivo')),
    created_by INTEGER NOT NULL REFERENCES "user"(id_user),
    creation_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_update_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deletion_date TIMESTAMP
);

CREATE TABLE IF NOT EXISTS logistics_shipment (
    id_logistics_shipment SERIAL PRIMARY KEY,
    id_customer_supplier INTEGER NOT NULL REFERENCES customer_supplier(id_customer_supplier),
    shipment_number VARCHAR(80) NOT NULL UNIQUE,
    bl_number VARCHAR(120),
    provider VARCHAR(180),
    transport_mode VARCHAR(60),
    cargo_type VARCHAR(120),
    origin_port VARCHAR(180),
    destination_port VARCHAR(180),
    customs VARCHAR(180),
    status VARCHAR(30) NOT NULL DEFAULT 'registrado'
        CHECK (status IN ('registrado', 'en tránsito', 'en aduana', 'liberado', 'entregado')),
    tracking TEXT,
    created_by INTEGER NOT NULL REFERENCES "user"(id_user),
    creation_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_update_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deletion_date TIMESTAMP
);

CREATE TABLE IF NOT EXISTS logistics_receivable (
    id_logistics_receivable SERIAL PRIMARY KEY,
    id_invoice INTEGER NOT NULL REFERENCES invoice(id_invoice),
    id_customer_supplier INTEGER NOT NULL REFERENCES customer_supplier(id_customer_supplier),
    amount NUMERIC(14,2) NOT NULL CHECK (amount >= 0),
    due_at DATE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pendiente' CHECK (status IN ('pendiente', 'pagado', 'vencido')),
    paid_at DATE,
    created_by INTEGER NOT NULL REFERENCES "user"(id_user),
    creation_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_update_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deletion_date TIMESTAMP
);

CREATE TABLE IF NOT EXISTS logistics_file (
    id_logistics_file SERIAL PRIMARY KEY,
    id_customer_supplier INTEGER NOT NULL REFERENCES customer_supplier(id_customer_supplier),
    folio VARCHAR(80) NOT NULL UNIQUE,
    origin TEXT NOT NULL,
    destination TEXT NOT NULL,
    id_logistics_branch INTEGER REFERENCES logistics_branch(id_logistics_branch),
    payment_form VARCHAR(10) NOT NULL DEFAULT '99',
    payment_method VARCHAR(10) NOT NULL DEFAULT 'PUE',
    cfdi_use VARCHAR(10) NOT NULL DEFAULT 'G03',
    status VARCHAR(20) NOT NULL DEFAULT 'abierto' CHECK (status IN ('abierto', 'facturando', 'facturado')),
    id_invoice INTEGER REFERENCES invoice(id_invoice),
    last_invoice_error TEXT,
    notes TEXT,
    created_by INTEGER NOT NULL REFERENCES "user"(id_user),
    creation_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_update_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deletion_date TIMESTAMP
);

ALTER TABLE logistics_trip
    ADD COLUMN IF NOT EXISTS id_logistics_file INTEGER REFERENCES logistics_file(id_logistics_file);

CREATE INDEX IF NOT EXISTS ix_logistics_shipment_client ON logistics_shipment(id_customer_supplier) WHERE deletion_date IS NULL;
CREATE INDEX IF NOT EXISTS ix_logistics_shipment_status ON logistics_shipment(status) WHERE deletion_date IS NULL;
CREATE INDEX IF NOT EXISTS ix_logistics_branch_status ON logistics_branch(status) WHERE deletion_date IS NULL;
CREATE INDEX IF NOT EXISTS ix_logistics_receivable_invoice ON logistics_receivable(id_invoice) WHERE deletion_date IS NULL;
CREATE INDEX IF NOT EXISTS ix_logistics_receivable_client ON logistics_receivable(id_customer_supplier) WHERE deletion_date IS NULL;
CREATE INDEX IF NOT EXISTS ix_logistics_receivable_status ON logistics_receivable(status, due_at) WHERE deletion_date IS NULL;
CREATE INDEX IF NOT EXISTS ix_logistics_file_client ON logistics_file(id_customer_supplier) WHERE deletion_date IS NULL;
CREATE INDEX IF NOT EXISTS ix_logistics_file_branch ON logistics_file(id_logistics_branch) WHERE deletion_date IS NULL;
CREATE INDEX IF NOT EXISTS ix_logistics_file_invoice ON logistics_file(id_invoice) WHERE deletion_date IS NULL;
CREATE INDEX IF NOT EXISTS ix_logistics_file_status ON logistics_file(status) WHERE deletion_date IS NULL;
CREATE INDEX IF NOT EXISTS ix_logistics_trip_file ON logistics_trip(id_logistics_file) WHERE deletion_date IS NULL;

INSERT INTO field (table_name, field_name, created_by, creation_date, last_update_date)
SELECT source_column.table_name, source_column.column_name, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
FROM information_schema.columns source_column
WHERE source_column.table_schema = 'public'
  AND source_column.table_name IN ('logistics_shipment', 'logistics_branch', 'logistics_receivable', 'logistics_file')
  AND NOT EXISTS (
      SELECT 1 FROM field
      WHERE field.table_name = source_column.table_name
        AND field.field_name = source_column.column_name
  );

INSERT INTO field (table_name, field_name, created_by, creation_date, last_update_date)
SELECT 'logistics_trip', 'id_logistics_file', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (
    SELECT 1 FROM field WHERE table_name = 'logistics_trip' AND field_name = 'id_logistics_file'
);

-- Guardado con un chequeo de existencia de scope_create: esta migracion es
-- anterior a 20260914110000_equipos_y_alcance_por_accion.sql (que agrega las
-- 4 columnas de alcance y suelta control_type), asi que en la PRIMERA pasada
-- completa contra un volumen nuevo todavia no existen -las agrega esa misma
-- migracion, mas adelante en la misma pasada-. Sin este guardado, la primera
-- pasada tronaria aqui con "column scope_create does not exist" antes de
-- llegar siquiera a la migracion que las crea. En pasadas posteriores (o en
-- cualquier base que ya paso por 20260914110000) la columna ya existe y el
-- bloque corre normal; si de verdad falta la fila para esta entidad se
-- resiembra sola en el siguiente reinicio del pod, que es cuando esta
-- condicion pasa a ser verdadera.
DO $$
BEGIN
IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'entity_permission' AND column_name = 'scope_create'
) THEN

CREATE TEMP TABLE tmp_ep_logistics_remaining AS
SELECT source_permission.id_permission, logistics_entity.entity_name,
       source_permission.scope_create, source_permission.scope_read,
       source_permission.scope_update, source_permission.scope_delete,
       'sidebar'::varchar AS menu_location, 'Logística'::varchar AS menu_group,
       'truck'::varchar AS menu_group_icon, logistics_entity.menu_label, logistics_entity.menu_order,
       1 AS created_by
FROM entity_permission source_permission
JOIN (VALUES
    ('logistics_shipment', 'customer_supplier', 'Embarques', 220),
    ('logistics_branch', 'invoice', 'Sucursales', 230),
    ('logistics_receivable', 'invoice', 'Cuentas por cobrar', 240),
    ('logistics_file', 'customer_supplier', 'Expedientes', 250)
) AS logistics_entity(entity_name, source_entity, menu_label, menu_order)
  ON source_permission.entity_name = logistics_entity.source_entity
WHERE source_permission.deletion_date IS NULL;

UPDATE entity_permission target SET
    scope_create = source.scope_create,
    scope_read = source.scope_read,
    scope_update = source.scope_update,
    scope_delete = source.scope_delete,
    menu_location = source.menu_location,
    menu_group = source.menu_group,
    menu_group_icon = source.menu_group_icon,
    menu_label = source.menu_label,
    menu_order = source.menu_order,
    deletion_date = NULL,
    last_update_date = CURRENT_TIMESTAMP
FROM tmp_ep_logistics_remaining source
WHERE target.id_permission = source.id_permission
  AND target.entity_name = source.entity_name;

INSERT INTO entity_permission (
    id_permission, entity_name, scope_create, scope_read, scope_update, scope_delete, menu_location, menu_group,
    menu_group_icon, menu_label, menu_order, created_by, creation_date, last_update_date
)
SELECT source.id_permission, source.entity_name,
       source.scope_create, source.scope_read, source.scope_update, source.scope_delete,
       source.menu_location, source.menu_group,
       source.menu_group_icon, source.menu_label, source.menu_order, source.created_by, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
FROM tmp_ep_logistics_remaining source
WHERE NOT EXISTS (
    SELECT 1 FROM entity_permission target
    WHERE target.id_permission = source.id_permission AND target.entity_name = source.entity_name
);

DROP TABLE tmp_ep_logistics_remaining;
END IF;
END $$;


INSERT INTO nm_field_permission (
    id_field, id_permission, control_type, created_by, creation_date, last_update_date
)
SELECT logistics_field.id_field, logistics_permission.id_permission, '15',
       1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
FROM field logistics_field
JOIN entity_permission logistics_permission
  ON logistics_permission.entity_name = logistics_field.table_name
WHERE logistics_field.table_name IN ('logistics_shipment', 'logistics_branch', 'logistics_receivable', 'logistics_file')
  AND logistics_permission.deletion_date IS NULL
  AND NOT EXISTS (
      SELECT 1 FROM nm_field_permission existing
      WHERE existing.id_field = logistics_field.id_field
        AND existing.id_permission = logistics_permission.id_permission
        AND existing.deletion_date IS NULL
  );

INSERT INTO nm_field_permission (
    id_field, id_permission, control_type, created_by, creation_date, last_update_date
)
SELECT trip_field.id_field, trip_permission.id_permission, '15',
       1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
FROM field trip_field
JOIN entity_permission trip_permission ON trip_permission.entity_name = 'logistics_trip'
WHERE trip_field.table_name = 'logistics_trip'
  AND trip_field.field_name = 'id_logistics_file'
  AND trip_permission.deletion_date IS NULL
  AND NOT EXISTS (
      SELECT 1 FROM nm_field_permission existing
      WHERE existing.id_field = trip_field.id_field
        AND existing.id_permission = trip_permission.id_permission
        AND existing.deletion_date IS NULL
  );