-- Capacidad de supervisar incidencias.
--
-- Antes cualquiera con permiso de lectura sobre incidencias veia las de toda
-- la empresa. Ahora una persona alcanza las suyas -las que reporto, las que
-- atiende y las que lidera- y quien supervisa las ve todas.
--
-- Se concede a los roles que ya tienen responsabilidad de mando.

BEGIN;

INSERT INTO entity_permission (id_permission, entity_name, control_type, menu_location, menu_order, created_by)
SELECT p.id_permission, 'incident_supervision', 2, 'hidden', 999, 1
FROM permission p
WHERE lower(p.permission_description) IN
      ('administrator', 'admin', 'gerente', 'gerente_administrativo', 'supervisor', 'jefe de taller')
  AND p.deletion_date IS NULL
  AND NOT EXISTS (
    SELECT 1 FROM entity_permission ep
    WHERE ep.id_permission = p.id_permission
      AND ep.entity_name = 'incident_supervision'
      AND ep.deletion_date IS NULL
  );

COMMIT;
