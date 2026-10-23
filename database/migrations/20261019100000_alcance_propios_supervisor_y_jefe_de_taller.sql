-- Alcance de LECTURA "Propios" (1) para Supervisor y Jefe de taller en lo que opera cada uno.
-- Hoy solo lo aplica el modulo BI (el guardia de las rutas sigue siendo booleano).
-- Una sola vez: las migraciones corren en cada arranque y esto pisaria lo que el
-- Gestor de roles cambie despues, asi que se deja una marca.
CREATE TABLE IF NOT EXISTS migration_once (name text PRIMARY KEY);

DO $$
DECLARE n integer;
BEGIN
    IF EXISTS (SELECT 1 FROM migration_once WHERE name = '20261019_alcance_propios') THEN
        RETURN;
    END IF;
    UPDATE entity_permission ep SET scope_read = 1
    FROM permission p
    WHERE p.id_permission = ep.id_permission AND ep.deletion_date IS NULL AND ep.scope_read = 4
      AND ((p.permission_description = 'Supervisor' AND ep.entity_name IN
              ('incident', 'incident_detail', 'nm_incident_product', 'proyect', 'proyect_material_need', 'task', 'task_note'))
        OR (p.permission_description = 'Jefe de taller' AND ep.entity_name IN
              ('incident', 'incident_detail', 'nm_incident_product', 'proyect', 'proyect_material_need', 'task', 'task_note')));
    GET DIAGNOSTICS n = ROW_COUNT;
    -- Almacen consulta TODOS los vales (solo lectura; escribir sigue siendo por la capacidad del vale).
    INSERT INTO entity_permission (id_permission, entity_name, menu_location, menu_order, created_by,
                                   creation_date, scope_create, scope_read, scope_update, scope_delete)
    SELECT p.id_permission, e.nombre, 'hidden', 100, 1, now(), 0, 4, 0, 0
    FROM permission p CROSS JOIN (VALUES ('incident'), ('incident_detail'), ('nm_incident_product')) AS e(nombre)
    WHERE p.permission_description = 'Almacenista'
    ON CONFLICT (id_permission, entity_name) DO NOTHING;
    -- Sin filas (instalacion nueva aun sin sembrar): no se marca, reintenta al siguiente arranque.
    IF n > 0 THEN
        INSERT INTO migration_once VALUES ('20261019_alcance_propios');
    END IF;
END $$;
