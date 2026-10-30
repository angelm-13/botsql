-- Gerencia en dos roles (2026-10-21): "Gerente Comercial" (revision: ve todo, no
-- autoriza proyectos) y "Gerente Tecnico" (campo: autoriza, ve menos).
--
-- Quien ya es "Gerente" sigue autorizando, asi que su rol pasa a llamarse
-- "Gerente Tecnico" CON SUS FILAS: ni se mueven usuarios ni se tocan permisos
-- (el Gestor manda; recortarle modulos a ese rol lo hace un administrador desde
-- el Gestor, no una migracion). "Gerente Comercial" lo siembra la resiembra
-- siguiente, vacio de usuarios.
--
-- Se reaplica en cada arranque, asi que tiene que ser idempotente: las
-- resiembras viejas insertan un "Gerente" si no existe ninguno vivo. Por eso:
--   * "Gerente" vivo con usuarios y sin "Gerente Tecnico"  -> se renombra.
--   * "Gerente" vivo sin usuarios (instalacion nueva, o el que una resiembra
--     vieja recreo)                                         -> se retira con
--     borrado logico, como "Jefe de almacen"; las resiembras ya no lo recrean
--     porque su NOT EXISTS no mira `deletion_date`.
--
-- Mayusculas: el "Gerente tecnico" que dejo la primera version de esta migracion
-- pasa a "Gerente Tecnico", conservando usuarios y filas.
--
-- Nombres viejos (tyakxa-dev): la primera version de esta migracion sembraba
-- "Gerente general" y "Gerente tecnico". Alli los administradores renombraron los
-- roles desde el Gestor a "Gerente Comercial" y "Gerente Tecnico", y la resiembra,
-- que crea por NOMBRE EXACTO, pudo volver a crear los viejos vacios. Un rol con el
-- nombre viejo, SIN usuarios y con su reemplazo ya vivo, se retira. Si tiene
-- usuarios no se toca: eso lo decide una persona.

BEGIN;

DO $$
DECLARE
    id_gerente INTEGER;
BEGIN
    -- 1. Duplicados vacios con el nombre viejo, cuando el nombre nuevo ya existe.
    UPDATE entity_permission SET deletion_date = CURRENT_TIMESTAMP
     WHERE deletion_date IS NULL
       AND id_permission IN (
           SELECT p.id_permission FROM permission p
            WHERE p.deletion_date IS NULL
              AND p.permission_description IN ('Gerente general', 'Gerente tecnico')
              AND NOT EXISTS (SELECT 1 FROM "user" u WHERE u.id_permission = p.id_permission)
              AND EXISTS (
                  SELECT 1 FROM permission nuevo
                   WHERE nuevo.deletion_date IS NULL
                     AND nuevo.permission_description = CASE p.permission_description
                         WHEN 'Gerente general' THEN 'Gerente Comercial'
                         ELSE 'Gerente Tecnico' END));

    UPDATE permission p SET deletion_date = CURRENT_TIMESTAMP
     WHERE p.deletion_date IS NULL
       AND p.permission_description IN ('Gerente general', 'Gerente tecnico')
       AND NOT EXISTS (SELECT 1 FROM "user" u WHERE u.id_permission = p.id_permission)
       AND EXISTS (
           SELECT 1 FROM permission nuevo
            WHERE nuevo.deletion_date IS NULL
              AND nuevo.permission_description = CASE p.permission_description
                  WHEN 'Gerente general' THEN 'Gerente Comercial'
                  ELSE 'Gerente Tecnico' END);

    -- 1b. El que ya tiene usuarios y solo difiere en mayusculas ("Gerente tecnico", que
    --     fue como la primera version de esta migracion renombro el "Gerente" de
    --     siempre) toma el nombre exacto: la resiembra busca por nombre exacto y, si no
    --     lo encontrara, sembraria un "Gerente Tecnico" nuevo y vacio al lado.
    UPDATE permission SET permission_description = 'Gerente Tecnico'
     WHERE deletion_date IS NULL
       AND permission_description <> 'Gerente Tecnico'
       AND lower(permission_description) = 'gerente tecnico'
       AND NOT EXISTS (SELECT 1 FROM permission otro
                        WHERE otro.deletion_date IS NULL
                          AND otro.permission_description = 'Gerente Tecnico');

    -- 2. El "Gerente" de siempre pasa a "Gerente Tecnico" con sus filas.
    SELECT id_permission INTO id_gerente FROM permission
     WHERE permission_description = 'Gerente' AND deletion_date IS NULL
     ORDER BY id_permission LIMIT 1;

    IF id_gerente IS NULL THEN
        RETURN;
    END IF;

    IF EXISTS (SELECT 1 FROM "user" WHERE id_permission = id_gerente)
       AND NOT EXISTS (SELECT 1 FROM permission
                        WHERE lower(permission_description) = 'gerente tecnico') THEN
        UPDATE permission SET permission_description = 'Gerente Tecnico'
         WHERE id_permission = id_gerente;
    ELSIF NOT EXISTS (SELECT 1 FROM "user" WHERE id_permission = id_gerente) THEN
        UPDATE entity_permission SET deletion_date = CURRENT_TIMESTAMP
         WHERE id_permission = id_gerente AND deletion_date IS NULL;
        UPDATE permission SET deletion_date = CURRENT_TIMESTAMP
         WHERE id_permission = id_gerente;
    END IF;
END $$;

COMMIT;
