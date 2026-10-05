-- El Gestor de roles y permisos manda sobre las migraciones, por construccion.
--
-- El problema (medido en adser-prod, 2026-10-02): `db-migrate` reaplica TODAS
-- las migraciones en cada arranque del backend (no hay tabla de control, ver
-- k8s/base/backend.yaml). Unas 25 de ellas hacen `UPDATE entity_permission`
-- sobre el menu (ubicacion, grupo, etiqueta, orden, icono) o sobre el alcance
-- (scope_*), y otras tocan `nm_field_permission` o borran filas. Cada vez que
-- se promovia un commit, esas sentencias reescribian lo que el administrador
-- habia dejado en el Gestor: la pasada de las 19:44 de ese dia reescribio 5
-- grupos de filas de entity_permission y 176 de nm_field_permission.
--
-- Parchar migracion por migracion no alcanza: ya habia una lista de "deuda
-- conocida" en test_manager_wins.py que el detector (una regex) no podia
-- seguir, y cada migracion nueva puede volver a abrir el hueco. Esta migracion
-- lo cierra en la base de datos, donde no se le puede escapar nada:
--
--   * `ajustado_por_gestor` guarda CUANDO toco la fila el Gestor. Lo escribe el
--     ORM (default al crear, onupdate al editar), asi que cualquier cambio
--     hecho desde la aplicacion cambia ese valor.
--   * Un UPDATE que NO cambia esa columna sobre una fila ya ajustada es de una
--     migracion (o de un psql a mano): se descarta. Lo mismo un DELETE fisico.
--   * Las filas que el Gestor nunca toco siguen igual que antes: las
--     migraciones las siembran y las corrigen como siempre, de modo que una
--     instalacion nueva sale con el menu y los alcances del registro.
--
-- Efectos a tener en cuenta
-- -------------------------
--   * Una fila ajustada ya no se mueve por migracion. Si alguna vez hace falta
--     reescribir a proposito una fila que el Gestor toco, la migracion debe
--     fijar tambien `ajustado_por_gestor` (el trigger deja pasar un UPDATE que
--     la cambia).
--   * El INSERT que repone permisos de campo no resucita uno que el Gestor
--     retiro (la baja del Gestor es logica, ver NmFieldPermissionService).
--
-- Congelado inicial
-- -----------------
-- En una base que YA estaba en uso (tiene las columnas scope_*, o sea que paso
-- por la Fase 1 de permisos) no hay forma de saber que filas editaron a mano,
-- y la proxima pasada de migraciones las pisaria. Por eso la PRIMERA vez que
-- se crea la columna se congela todo lo que hay: lo vigente en ese momento es
-- la verdad. En una instalacion nueva no se congela nada -- todavia no hay
-- nada que alguien haya decidido.
--
-- Se reaplica en cada arranque: la columna, el congelado (solo si la columna
-- no existia) y las funciones/triggers son idempotentes.

BEGIN;

DO $$
DECLARE
    primera_vez boolean;
BEGIN
    primera_vez := NOT EXISTS (
        SELECT 1 FROM information_schema.columns
         WHERE table_schema = 'public'
           AND table_name = 'entity_permission'
           AND column_name = 'ajustado_por_gestor'
    );

    ALTER TABLE entity_permission ADD COLUMN IF NOT EXISTS ajustado_por_gestor TIMESTAMP;
    ALTER TABLE nm_field_permission ADD COLUMN IF NOT EXISTS ajustado_por_gestor TIMESTAMP;

    IF primera_vez AND EXISTS (
        SELECT 1 FROM information_schema.columns
         WHERE table_schema = 'public'
           AND table_name = 'entity_permission'
           AND column_name = 'scope_create'
    ) THEN
        UPDATE entity_permission SET ajustado_por_gestor = now();
        UPDATE nm_field_permission SET ajustado_por_gestor = now();
    END IF;
END $$;

-- Descarta lo que no viene del Gestor sobre una fila que el Gestor ya toco.
-- `RETURN NULL` en un trigger BEFORE ... FOR EACH ROW omite esa fila sin error.
CREATE OR REPLACE FUNCTION proteger_ajuste_del_gestor() RETURNS trigger
LANGUAGE plpgsql AS $fn$
BEGIN
    IF TG_OP = 'DELETE' THEN
        IF OLD.ajustado_por_gestor IS NOT NULL THEN
            RETURN NULL;
        END IF;
        RETURN OLD;
    END IF;

    IF OLD.ajustado_por_gestor IS NOT NULL
       AND NEW.ajustado_por_gestor IS NOT DISTINCT FROM OLD.ajustado_por_gestor THEN
        RETURN NULL;
    END IF;
    RETURN NEW;
END
$fn$;

-- Un permiso de campo que el Gestor retiro no vuelve con el INSERT de
-- reposicion de las migraciones (que solo mira si hay uno VIGENTE). Un INSERT
-- del Gestor trae `ajustado_por_gestor` y pasa siempre.
CREATE OR REPLACE FUNCTION no_resucitar_permiso_de_campo() RETURNS trigger
LANGUAGE plpgsql AS $fn$
BEGIN
    IF NEW.ajustado_por_gestor IS NULL AND EXISTS (
        SELECT 1 FROM nm_field_permission previo
         WHERE previo.id_field = NEW.id_field
           AND previo.id_permission = NEW.id_permission
           AND previo.deletion_date IS NOT NULL
           AND previo.ajustado_por_gestor IS NOT NULL
    ) THEN
        RETURN NULL;
    END IF;
    RETURN NEW;
END
$fn$;

DROP TRIGGER IF EXISTS trg_gestor_manda ON entity_permission;
CREATE TRIGGER trg_gestor_manda
    BEFORE UPDATE OR DELETE ON entity_permission
    FOR EACH ROW EXECUTE FUNCTION proteger_ajuste_del_gestor();

DROP TRIGGER IF EXISTS trg_gestor_manda ON nm_field_permission;
CREATE TRIGGER trg_gestor_manda
    BEFORE UPDATE OR DELETE ON nm_field_permission
    FOR EACH ROW EXECUTE FUNCTION proteger_ajuste_del_gestor();

DROP TRIGGER IF EXISTS trg_no_resucitar ON nm_field_permission;
CREATE TRIGGER trg_no_resucitar
    BEFORE INSERT ON nm_field_permission
    FOR EACH ROW EXECUTE FUNCTION no_resucitar_permiso_de_campo();

COMMIT;
