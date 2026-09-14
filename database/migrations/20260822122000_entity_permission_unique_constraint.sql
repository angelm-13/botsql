-- Agrega el constraint UNIQUE que varias migraciones posteriores (logistica,
-- appointments, project_management, seed_entity_permissions, module_permission_matrix)
-- ya asumen que existe: todas usan `ON CONFLICT (id_permission, entity_name)`,
-- pero `entity_permission` nunca tuvo mas que su PRIMARY KEY propio
-- (id_entity_permission) mas indices simples por separado en cada columna.
-- Sin el constraint, Postgres rechaza esas migraciones con
-- 42P10 (no unique or exclusion constraint matching the ON CONFLICT
-- specification) y el db-migrate se detiene ahi, sin llegar siquiera a las
-- migraciones de CFDI/inventario.

BEGIN;

-- Antes de poder agregar el UNIQUE hay que garantizar que no existan filas
-- duplicadas por (id_permission, entity_name). Como el constraint nunca
-- existio, no hay garantia de que las inserciones directas (fuera de las
-- migraciones que ya usan ON CONFLICT) no hayan dejado duplicados. Se
-- conserva la fila mas reciente (mayor id_entity_permission) de cada par y
-- se descartan las demas.
DELETE FROM entity_permission a
USING entity_permission b
WHERE a.id_permission = b.id_permission
  AND a.entity_name = b.entity_name
  AND a.id_entity_permission < b.id_entity_permission;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'uq_entity_permission_permission_entity'
    ) THEN
        ALTER TABLE entity_permission
            ADD CONSTRAINT uq_entity_permission_permission_entity
            UNIQUE (id_permission, entity_name);
    END IF;
END $$;

COMMIT;
