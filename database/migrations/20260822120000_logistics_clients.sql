ALTER TABLE customer_supplier
    ADD COLUMN IF NOT EXISTS sla_level VARCHAR(20) NOT NULL DEFAULT 'standard',
    ADD COLUMN IF NOT EXISTS credit_limit NUMERIC(14,2) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS logistics_notes TEXT;

ALTER TABLE customer_supplier
    DROP CONSTRAINT IF EXISTS ck_customer_supplier_sla_level;

ALTER TABLE customer_supplier
    ADD CONSTRAINT ck_customer_supplier_sla_level
    CHECK (sla_level IN ('standard', 'premium'));

ALTER TABLE customer_supplier
    DROP CONSTRAINT IF EXISTS ck_customer_supplier_credit_limit;

ALTER TABLE customer_supplier
    ADD CONSTRAINT ck_customer_supplier_credit_limit
    CHECK (credit_limit >= 0);

INSERT INTO field (table_name, field_name, created_by, creation_date, last_update_date)
SELECT 'customer_supplier', field_name, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
FROM (VALUES ('sla_level'), ('credit_limit'), ('logistics_notes')) AS logistics_fields(field_name)
WHERE NOT EXISTS (
        SELECT 1 FROM field
        WHERE field.table_name = 'customer_supplier'
            AND field.field_name = logistics_fields.field_name
);

INSERT INTO nm_field_permission (
        id_field, id_permission, control_type, created_by, creation_date, last_update_date
)
SELECT new_field.id_field, existing_permission.id_permission,
             MAX(existing_permission.control_type), 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
FROM field new_field
JOIN nm_field_permission existing_permission
    ON existing_permission.id_field IN (
            SELECT id_field FROM field
            WHERE table_name = 'customer_supplier' AND field_name = 'name'
    )
WHERE new_field.table_name = 'customer_supplier'
    AND new_field.field_name IN ('sla_level', 'credit_limit', 'logistics_notes')
    AND existing_permission.deletion_date IS NULL
    AND NOT EXISTS (
            SELECT 1 FROM nm_field_permission current_permission
            WHERE current_permission.id_field = new_field.id_field
                AND current_permission.id_permission = existing_permission.id_permission
                AND current_permission.deletion_date IS NULL
    )
GROUP BY new_field.id_field, existing_permission.id_permission;