
CREATE TABLE IF NOT EXISTS "entity_permission" (
  "id_entity_permission" SERIAL PRIMARY KEY,
  "id_permission" INTEGER NOT NULL,
  "entity_name" VARCHAR(120) NOT NULL,
  "control_type" SMALLINT NOT NULL DEFAULT 15,
  "created_by" INTEGER NOT NULL DEFAULT 1,
  "creation_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "last_update_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "deletion_date" TIMESTAMP NULL,
  CONSTRAINT "uq_entity_permission_scope" UNIQUE ("id_permission", "entity_name"),
  CONSTRAINT "ck_entity_permission_control_type" CHECK ("control_type" BETWEEN 1 AND 15)
);

CREATE INDEX IF NOT EXISTS "idx_entity_permission_lookup"
  ON "entity_permission" ("id_permission", "entity_name", "control_type");

CREATE TABLE IF NOT EXISTS "audit_log" (
  "id_audit_log" SERIAL PRIMARY KEY,
  "id_user" INTEGER NULL,
  "event_type" VARCHAR(80) NOT NULL,
  "entity_name" VARCHAR(120) NULL,
  "action" VARCHAR(40) NULL,
  "metadata_json" JSONB NOT NULL DEFAULT '{}'::jsonb,
  "creation_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS "idx_audit_log_user" ON "audit_log" ("id_user");
CREATE INDEX IF NOT EXISTS "idx_audit_log_entity" ON "audit_log" ("entity_name");
CREATE INDEX IF NOT EXISTS "idx_audit_log_type" ON "audit_log" ("event_type");
