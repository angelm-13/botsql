-- Gerencia en dos roles (2026-10-21): "Gerente general" (ve todo, no autoriza
-- proyectos) y "Gerente tecnico" (autoriza, ve menos).
--
-- Quien ya es "Gerente" sigue autorizando, asi que su rol pasa a llamarse
-- "Gerente tecnico" CON SUS FILAS: ni se mueven usuarios ni se tocan permisos
-- (el Gestor manda; recortarle modulos a ese rol lo hace un administrador desde
-- el Gestor, no una migracion). "Gerente general" lo siembra la resiembra
-- siguiente, vacio de usuarios.
--
-- Se reaplica en cada arranque, asi que tiene que ser idempotente: las
-- resiembras viejas insertan un "Gerente" si no existe ninguno vivo. Por eso:
--   * "Gerente" vivo con usuarios y sin "Gerente tecnico"  -> se renombra.
--   * "Gerente" vivo sin usuarios (instalacion nueva, o el que una resiembra
--     vieja recreo)                                         -> se retira con
--     borrado logico, como "Jefe de almacen"; las resiembras ya no lo recrean
--     porque su NOT EXISTS no mira `deletion_date`.

BEGIN;

DO $$
DECLARE
    id_gerente INTEGER;
BEGIN
    SELECT id_permission INTO id_gerente FROM permission
     WHERE permission_description = 'Gerente' AND deletion_date IS NULL
     ORDER BY id_permission LIMIT 1;

    IF id_gerente IS NULL THEN
        RETURN;
    END IF;

    IF EXISTS (SELECT 1 FROM "user" WHERE id_permission = id_gerente)
       AND NOT EXISTS (SELECT 1 FROM permission
                        WHERE lower(permission_description) = 'gerente tecnico') THEN
        UPDATE permission SET permission_description = 'Gerente tecnico'
         WHERE id_permission = id_gerente;
    ELSIF NOT EXISTS (SELECT 1 FROM "user" WHERE id_permission = id_gerente) THEN
        UPDATE entity_permission SET deletion_date = CURRENT_TIMESTAMP
         WHERE id_permission = id_gerente AND deletion_date IS NULL;
        UPDATE permission SET deletion_date = CURRENT_TIMESTAMP
         WHERE id_permission = id_gerente;
    END IF;
END $$;

COMMIT;
