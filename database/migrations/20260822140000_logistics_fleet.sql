CREATE TABLE IF NOT EXISTS logistics_unit (
    id_logistics_unit SERIAL PRIMARY KEY,
    plate VARCHAR(30) NOT NULL UNIQUE,
    unit_type VARCHAR(80) NOT NULL,
    mileage NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (mileage >= 0),
    availability_status VARCHAR(30) NOT NULL DEFAULT 'disponible'
        CHECK (availability_status IN ('disponible', 'en viaje', 'mantenimiento', 'fuera de servicio')),
    insurance_expiration DATE,
    verification_expiration DATE,
    policy_number VARCHAR(100),
    fuel_efficiency NUMERIC(10,2) CHECK (fuel_efficiency >= 0),
    status VARCHAR(20) NOT NULL DEFAULT 'activo' CHECK (status IN ('activo', 'inactivo')),
    created_by INTEGER NOT NULL REFERENCES "user"(id_user),
    creation_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_update_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deletion_date TIMESTAMP
);

CREATE TABLE IF NOT EXISTS logistics_trailer (
    id_logistics_trailer SERIAL PRIMARY KEY,
    plate VARCHAR(30) NOT NULL UNIQUE,
    trailer_type VARCHAR(80) NOT NULL,
    capacity NUMERIC(12,2) CHECK (capacity >= 0),
    status VARCHAR(20) NOT NULL DEFAULT 'activo' CHECK (status IN ('activo', 'inactivo')),
    created_by INTEGER NOT NULL REFERENCES "user"(id_user),
    creation_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_update_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deletion_date TIMESTAMP
);

CREATE TABLE IF NOT EXISTS logistics_operator (
    id_logistics_operator SERIAL PRIMARY KEY,
    full_name VARCHAR(150) NOT NULL,
    license_number VARCHAR(80) NOT NULL UNIQUE,
    license_expiration DATE,
    status VARCHAR(20) NOT NULL DEFAULT 'activo' CHECK (status IN ('activo', 'inactivo')),
    contact_phone VARCHAR(40),
    performance_score NUMERIC(5,2) NOT NULL DEFAULT 0 CHECK (performance_score >= 0),
    created_by INTEGER NOT NULL REFERENCES "user"(id_user),
    creation_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_update_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deletion_date TIMESTAMP
);

CREATE TABLE IF NOT EXISTS logistics_maintenance (
    id_logistics_maintenance SERIAL PRIMARY KEY,
    id_logistics_unit INTEGER NOT NULL REFERENCES logistics_unit(id_logistics_unit),
    maintenance_type VARCHAR(80) NOT NULL,
    scheduled_at DATE,
    closed_at DATE,
    cost NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK (cost >= 0),
    status VARCHAR(20) NOT NULL DEFAULT 'abierta' CHECK (status IN ('abierta', 'en proceso', 'cerrada')),
    description TEXT,
    created_by INTEGER NOT NULL REFERENCES "user"(id_user),
    creation_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_update_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deletion_date TIMESTAMP,
    CHECK (closed_at IS NULL OR scheduled_at IS NULL OR closed_at >= scheduled_at),
    CHECK ((status = 'cerrada' AND closed_at IS NOT NULL) OR (status <> 'cerrada' AND closed_at IS NULL))
);

CREATE INDEX IF NOT EXISTS ix_logistics_unit_availability
    ON logistics_unit(availability_status) WHERE deletion_date IS NULL;
CREATE INDEX IF NOT EXISTS ix_logistics_trailer_type
    ON logistics_trailer(trailer_type) WHERE deletion_date IS NULL;
CREATE INDEX IF NOT EXISTS ix_logistics_operator_status
    ON logistics_operator(status) WHERE deletion_date IS NULL;
CREATE INDEX IF NOT EXISTS ix_logistics_maintenance_unit
    ON logistics_maintenance(id_logistics_unit) WHERE deletion_date IS NULL;
CREATE INDEX IF NOT EXISTS ix_logistics_maintenance_status
    ON logistics_maintenance(status, scheduled_at) WHERE deletion_date IS NULL;

INSERT INTO field (table_name, field_name, created_by, creation_date, last_update_date)
SELECT source_column.table_name, source_column.column_name, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
FROM information_schema.columns source_column
WHERE source_column.table_schema = 'public'
  AND source_column.table_name IN ('logistics_unit', 'logistics_trailer', 'logistics_operator', 'logistics_maintenance')
  AND NOT EXISTS (
      SELECT 1 FROM field
      WHERE field.table_name = source_column.table_name
        AND field.field_name = source_column.column_name
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

CREATE TEMP TABLE tmp_ep_logistics_fleet AS
SELECT source_permission.id_permission, logistics_entity.entity_name,
       source_permission.scope_create, source_permission.scope_read,
       source_permission.scope_update, source_permission.scope_delete,
       'sidebar'::varchar AS menu_location, 'Logística'::varchar AS menu_group,
       'truck'::varchar AS menu_group_icon, logistics_entity.menu_label, logistics_entity.menu_order,
       1 AS created_by
FROM entity_permission source_permission
CROSS JOIN (VALUES
    ('logistics_unit', 'Unidades', 90),
    ('logistics_trailer', 'Remolques', 100),
    ('logistics_operator', 'Operadores', 110),
    ('logistics_maintenance', 'Mantenimientos', 120)
) AS logistics_entity(entity_name, menu_label, menu_order)
WHERE source_permission.entity_name = 'customer_supplier'
  AND source_permission.deletion_date IS NULL;

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
FROM tmp_ep_logistics_fleet source
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
FROM tmp_ep_logistics_fleet source
WHERE NOT EXISTS (
    SELECT 1 FROM entity_permission target
    WHERE target.id_permission = source.id_permission AND target.entity_name = source.entity_name
);

DROP TABLE tmp_ep_logistics_fleet;
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
WHERE logistics_field.table_name IN ('logistics_unit', 'logistics_trailer', 'logistics_operator', 'logistics_maintenance')
  AND logistics_permission.deletion_date IS NULL
  AND NOT EXISTS (
      SELECT 1 FROM nm_field_permission existing
      WHERE existing.id_field = logistics_field.id_field
        AND existing.id_permission = logistics_permission.id_permission
        AND existing.deletion_date IS NULL
  );