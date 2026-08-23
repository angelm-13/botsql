CREATE TABLE IF NOT EXISTS logistics_quotation (
    id_logistics_quotation SERIAL PRIMARY KEY,
    id_customer_supplier INTEGER NOT NULL REFERENCES customer_supplier(id_customer_supplier),
    folio VARCHAR(80) NOT NULL UNIQUE,
    service_type VARCHAR(100) NOT NULL,
    origin TEXT NOT NULL,
    destination TEXT NOT NULL,
    cargo_type VARCHAR(120),
    unit_required VARCHAR(120),
    kilometers NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (kilometers >= 0),
    maneuvers NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK (maneuvers >= 0),
    storage NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK (storage >= 0),
    additional_services JSONB NOT NULL DEFAULT '{}'::jsonb,
    total NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK (total >= 0),
    source_branch_reference VARCHAR(120),
    status VARCHAR(30) NOT NULL DEFAULT 'borrador'
        CHECK (status IN ('borrador', 'enviada', 'aceptada', 'rechazada', 'vencida', 'cancelada')),
    created_by INTEGER NOT NULL REFERENCES "user"(id_user),
    creation_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_update_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deletion_date TIMESTAMP
);

CREATE TABLE IF NOT EXISTS logistics_service_request (
    id_logistics_service_request SERIAL PRIMARY KEY,
    id_customer_supplier INTEGER NOT NULL REFERENCES customer_supplier(id_customer_supplier),
    id_logistics_quotation INTEGER REFERENCES logistics_quotation(id_logistics_quotation),
    request_number VARCHAR(80) NOT NULL UNIQUE,
    request_type VARCHAR(100) NOT NULL,
    origin TEXT,
    destination TEXT,
    requested_pickup_at TIMESTAMP,
    requested_delivery_at TIMESTAMP,
    status VARCHAR(30) NOT NULL DEFAULT 'solicitado'
        CHECK (status IN ('solicitado', 'aprobado', 'programado', 'cancelado')),
    priority VARCHAR(20) NOT NULL DEFAULT 'normal'
        CHECK (priority IN ('baja', 'normal', 'alta', 'urgente')),
    description TEXT,
    created_by INTEGER NOT NULL REFERENCES "user"(id_user),
    creation_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_update_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deletion_date TIMESTAMP,
    CHECK (requested_delivery_at IS NULL OR requested_pickup_at IS NULL OR requested_delivery_at >= requested_pickup_at)
);

CREATE TABLE IF NOT EXISTS logistics_trip (
    id_logistics_trip SERIAL PRIMARY KEY,
    id_logistics_service_request INTEGER NOT NULL REFERENCES logistics_service_request(id_logistics_service_request),
    id_customer_supplier INTEGER NOT NULL REFERENCES customer_supplier(id_customer_supplier),
    folio VARCHAR(80) NOT NULL UNIQUE,
    id_logistics_unit INTEGER REFERENCES logistics_unit(id_logistics_unit),
    id_logistics_trailer INTEGER REFERENCES logistics_trailer(id_logistics_trailer),
    id_logistics_operator INTEGER REFERENCES logistics_operator(id_logistics_operator),
    supplier_reference VARCHAR(120),
    route_reference VARCHAR(120),
    expediente_reference VARCHAR(120),
    status VARCHAR(30) NOT NULL DEFAULT 'solicitado'
        CHECK (status IN ('solicitado', 'planeado', 'asignado', 'cargado', 'en tránsito', 'en ruta', 'retrasado', 'entregado', 'cerrado', 'facturado', 'cancelado')),
    planned_pickup_at TIMESTAMP,
    planned_delivery_at TIMESTAMP,
    actual_pickup_at TIMESTAMP,
    actual_delivery_at TIMESTAMP,
    planned_cost NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK (planned_cost >= 0),
    actual_cost NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK (actual_cost >= 0),
    revenue NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK (revenue >= 0),
    kilometers NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (kilometers >= 0),
    restrictions TEXT,
    created_by INTEGER NOT NULL REFERENCES "user"(id_user),
    creation_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_update_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deletion_date TIMESTAMP,
    CHECK (planned_delivery_at IS NULL OR planned_pickup_at IS NULL OR planned_delivery_at >= planned_pickup_at),
    CHECK (actual_delivery_at IS NULL OR actual_pickup_at IS NULL OR actual_delivery_at >= actual_pickup_at)
);

CREATE TABLE IF NOT EXISTS logistics_evidence (
    id_logistics_evidence SERIAL PRIMARY KEY,
    id_logistics_trip INTEGER NOT NULL REFERENCES logistics_trip(id_logistics_trip),
    evidence_type VARCHAR(80) NOT NULL,
    photo_path VARCHAR(300),
    signature_path VARCHAR(300),
    source_document_reference VARCHAR(120),
    latitude NUMERIC(10,7) CHECK (latitude IS NULL OR latitude BETWEEN -90 AND 90),
    longitude NUMERIC(10,7) CHECK (longitude IS NULL OR longitude BETWEEN -180 AND 180),
    comments TEXT,
    captured_by INTEGER REFERENCES "user"(id_user),
    captured_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER NOT NULL REFERENCES "user"(id_user),
    creation_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_update_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deletion_date TIMESTAMP
);

CREATE TABLE IF NOT EXISTS logistics_incident (
    id_logistics_incident SERIAL PRIMARY KEY,
    id_logistics_trip INTEGER NOT NULL REFERENCES logistics_trip(id_logistics_trip),
    incident_type VARCHAR(100) NOT NULL,
    severity VARCHAR(20) NOT NULL DEFAULT 'media'
        CHECK (severity IN ('baja', 'media', 'alta', 'critica')),
    description TEXT NOT NULL,
    responsible_user_id INTEGER REFERENCES "user"(id_user),
    status VARCHAR(20) NOT NULL DEFAULT 'abierta'
        CHECK (status IN ('abierta', 'en_proceso', 'resuelta', 'cerrada', 'cancelada')),
    created_by INTEGER NOT NULL REFERENCES "user"(id_user),
    creation_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_update_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deletion_date TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_logistics_quotation_client ON logistics_quotation(id_customer_supplier) WHERE deletion_date IS NULL;
CREATE INDEX IF NOT EXISTS ix_logistics_quotation_status ON logistics_quotation(status) WHERE deletion_date IS NULL;
CREATE INDEX IF NOT EXISTS ix_logistics_service_request_client ON logistics_service_request(id_customer_supplier) WHERE deletion_date IS NULL;
CREATE INDEX IF NOT EXISTS ix_logistics_service_request_quotation ON logistics_service_request(id_logistics_quotation) WHERE deletion_date IS NULL;
CREATE INDEX IF NOT EXISTS ix_logistics_service_request_status ON logistics_service_request(status, priority) WHERE deletion_date IS NULL;
CREATE INDEX IF NOT EXISTS ix_logistics_trip_request ON logistics_trip(id_logistics_service_request) WHERE deletion_date IS NULL;
CREATE INDEX IF NOT EXISTS ix_logistics_trip_client ON logistics_trip(id_customer_supplier) WHERE deletion_date IS NULL;
CREATE INDEX IF NOT EXISTS ix_logistics_trip_assignment ON logistics_trip(id_logistics_unit, id_logistics_trailer, id_logistics_operator) WHERE deletion_date IS NULL;
CREATE INDEX IF NOT EXISTS ix_logistics_trip_status ON logistics_trip(status, planned_pickup_at) WHERE deletion_date IS NULL;
CREATE INDEX IF NOT EXISTS ix_logistics_evidence_trip ON logistics_evidence(id_logistics_trip) WHERE deletion_date IS NULL;
CREATE INDEX IF NOT EXISTS ix_logistics_incident_trip ON logistics_incident(id_logistics_trip) WHERE deletion_date IS NULL;
CREATE INDEX IF NOT EXISTS ix_logistics_incident_status ON logistics_incident(status, severity) WHERE deletion_date IS NULL;

INSERT INTO field (table_name, field_name, created_by, creation_date, last_update_date)
SELECT source_column.table_name, source_column.column_name, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
FROM information_schema.columns source_column
WHERE source_column.table_schema = 'public'
  AND source_column.table_name IN ('logistics_quotation', 'logistics_service_request', 'logistics_trip', 'logistics_evidence', 'logistics_incident')
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
    ('logistics_quotation', 'Cotizaciones', 170),
    ('logistics_service_request', 'Solicitudes', 180),
    ('logistics_trip', 'Viajes', 190),
    ('logistics_evidence', 'Evidencias', 200),
    ('logistics_incident', 'Incidencias', 210)
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
WHERE logistics_field.table_name IN ('logistics_quotation', 'logistics_service_request', 'logistics_trip', 'logistics_evidence', 'logistics_incident')
  AND logistics_permission.deletion_date IS NULL
  AND NOT EXISTS (
      SELECT 1 FROM nm_field_permission existing
      WHERE existing.id_field = logistics_field.id_field
        AND existing.id_permission = logistics_permission.id_permission
        AND existing.deletion_date IS NULL
  );