ALTER TABLE entity_permission
    ADD COLUMN IF NOT EXISTS menu_location VARCHAR(20) NOT NULL DEFAULT 'sidebar',
    ADD COLUMN IF NOT EXISTS menu_group VARCHAR(80),
    ADD COLUMN IF NOT EXISTS menu_label VARCHAR(100),
    ADD COLUMN IF NOT EXISTS menu_order INTEGER NOT NULL DEFAULT 100;

ALTER TABLE entity_permission
    DROP CONSTRAINT IF EXISTS ck_entity_permission_menu_location;

ALTER TABLE entity_permission
    ADD CONSTRAINT ck_entity_permission_menu_location
    CHECK (menu_location IN ('sidebar', 'settings', 'hidden'));

CREATE INDEX IF NOT EXISTS ix_entity_permission_navigation
    ON entity_permission (id_permission, menu_location, menu_group, menu_order)
    WHERE deletion_date IS NULL;