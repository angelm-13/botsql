-- Equipos de usuarios y alcance por accion en el gestor de roles.
--
-- De que se parte
-- ---------------
-- `entity_permission.control_type` era una sola mascara de bits: CREAR=1,
-- LEER=2, ACTUALIZAR=4, ELIMINAR=8, combinados en un entero (15 = las
-- cuatro). El gestor de roles pintaba un checkbox por bit. No existia forma
-- de decir "esto se ve, pero solo lo propio" -- un permiso era booleano,
-- todo o nada.
--
-- Que cambia
-- ----------
-- Cada una de las cuatro acciones pasa de booleano a un ALCANCE: 0 Sin
-- acceso, 1 Propios, 2 Mis grupos, 4 Todos -- valores de bit para poder
-- combinarlos a futuro (3, 5, 6, 7) sin volver a tocar el esquema. Van en
-- cuatro columnas independientes y no en una sola reempacada: las cuatro
-- acciones ya eran independientes entre si y seguir asi evita tener que
-- desplazar bits para leer o escribir una sola accion.
--
-- Dato existente: `control_type` encendido (cualquier bit) se convierte en
-- Todos (4) para esa accion. Nadie pierde hoy el acceso que ya tenia; ajustar
-- a Propios/Mis grupos es una decision posterior, rol por rol, desde el
-- gestor. El propio filtrado real por alcance (que hace que Propios/Mis
-- grupos limiten de verdad lo que se ve) NO se conecta en esta migracion --
-- las cuatro columnas ya gobiernan el acceso booleano de siempre (0 deniega,
-- cualquier otro valor permite), pero todavia no distinguen entre ellas.
--
-- `nm_field_permission.control_type` (visibilidad de campo, bit 2) no se
-- toca: es un concepto aparte, no una de estas cuatro acciones.
--
-- Equipos
-- -------
-- No existia ningun concepto de equipo/grupo de usuarios. `user.supervisor`
-- es un entero suelto sin llave foranea y sin uso real en ningun servicio; no
-- sirve como base. `team`/`nm_team_user` son la pieza nueva, sin datos que
-- migrar. Se llama `team` y no `group` para no chocar con la palabra
-- reservada de SQL `group` y para no confundirla con la columna
-- `entity_permission.menu_group`, que es la agrupacion visual del menu y no
-- tiene nada que ver con esto.

BEGIN;

CREATE TABLE IF NOT EXISTS "team" (
    id_team           SERIAL PRIMARY KEY,
    team_description  VARCHAR(150) NOT NULL,
    created_by        INTEGER NOT NULL DEFAULT 1,
    creation_date     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_update_date  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deletion_date     TIMESTAMP
);

CREATE TABLE IF NOT EXISTS nm_team_user (
    id_nm_team_user   SERIAL PRIMARY KEY,
    id_team           INTEGER NOT NULL REFERENCES "team"(id_team),
    id_user           INTEGER NOT NULL REFERENCES "user"(id_user),
    created_by        INTEGER NOT NULL DEFAULT 1,
    creation_date     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_update_date  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deletion_date     TIMESTAMP,
    CONSTRAINT uq_nm_team_user UNIQUE (id_team, id_user)
);

-- --- alcance por accion, en vez de un solo booleano combinado ------------

ALTER TABLE entity_permission
    ADD COLUMN IF NOT EXISTS scope_create SMALLINT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS scope_read   SMALLINT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS scope_update SMALLINT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS scope_delete SMALLINT NOT NULL DEFAULT 0;

-- `control_type` esta declarado `SmallInteger` en el modelo pero vive como
-- `text` en la base real (deuda ya senalada en
-- `seed_module_permissions.py`, aparte de esta migracion); de ahi el cast
-- explicito antes de la mascara de bits.
--
-- Guardado con un chequeo de existencia: esta migracion se reaplica en cada
-- arranque del pod (ver hallazgo sobre como corren las migraciones de
-- verdad, sin ninguna tabla de control). En la SEGUNDA pasada en adelante
-- `control_type` ya no existe -esta misma migracion la elimino en la
-- primera-, asi que sin este guardado el UPDATE tronaria con "column
-- control_type does not exist" desde el segundo arranque.
DO $$
BEGIN
IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'entity_permission' AND column_name = 'control_type'
) THEN

UPDATE entity_permission
   SET scope_create = CASE WHEN (control_type::integer & 1) = 1 THEN 4 ELSE 0 END,
       scope_read   = CASE WHEN (control_type::integer & 2) = 2 THEN 4 ELSE 0 END,
       scope_update = CASE WHEN (control_type::integer & 4) = 4 THEN 4 ELSE 0 END,
       scope_delete = CASE WHEN (control_type::integer & 8) = 8 THEN 4 ELSE 0 END
 WHERE control_type IS NOT NULL;

ALTER TABLE entity_permission DROP COLUMN control_type;

END IF;
END $$;

COMMIT;
