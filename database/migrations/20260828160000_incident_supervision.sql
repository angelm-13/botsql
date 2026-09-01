-- Capacidad de supervisar incidencias.
--
-- Antes cualquiera con permiso de lectura sobre incidencias veia las de toda
-- la empresa. Ahora una persona alcanza las suyas -las que reporto, las que
-- atiende y las que lidera- y quien supervisa las ve todas.
--
-- Se concede a los roles que ya tienen responsabilidad de mando.
--
-- ON CONFLICT en vez de NOT EXISTS (deletion_date IS NULL): mismo motivo que
-- 20260828140000 -- 20260828240000 da de baja logica toda la tabla y la
-- resiembra desde el registro de modulos, y esta entidad puede quedar fuera
-- de esa resiembra para alguno de estos roles. Un reinicio del pod reaplica
-- las 45 migraciones desde cero, y un NOT EXISTS que solo mira filas activas
-- choca contra la fila fantasma que dejo la resiembra anterior.

BEGIN;

INSERT INTO entity_permission (id_permission, entity_name, control_type, menu_location, menu_order, created_by)
SELECT p.id_permission, 'incident_supervision', 2, 'hidden', 999, 1
FROM permission p
WHERE lower(p.permission_description) IN
      ('administrator', 'admin', 'gerente', 'gerente_administrativo', 'supervisor', 'jefe de taller')
  AND p.deletion_date IS NULL
ON CONFLICT (id_permission, entity_name) DO NOTHING;

COMMIT;
