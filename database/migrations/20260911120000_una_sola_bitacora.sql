-- Una sola bitacora: `audit_log` se funde en `event_log`.
--
-- Por que habia dos
-- -----------------
-- `event_log` es la bitacora del sistema: la escribe `base_service` en cada
-- alta, cambio y baja de cualquier entidad. Pero su columna `action` tenia
--
--     CHECK (action IN ('create', 'update', 'delete'))
--
-- y eso dejaba fuera todo lo que no es un CRUD: un permiso denegado, el cambio
-- de estatus de un vale, una mesa que se cobro. Quien necesito registrar eso no
-- pudo usar `event_log`, asi que aparecio `audit_log` -- otra tabla, otro
-- modelo, otra consulta -- para lo mismo.
--
-- La restriccion era la causa, no el sintoma. Se ensancha, y la segunda tabla
-- deja de tener motivo para existir.
--
-- Que se pierde
-- -------------
-- Nada. `audit_log` estaba en CERO filas -- se conto antes de borrarla --, asi
-- que no hay historial que trasladar. Los 16 asientos de `event_log` siguen
-- donde estaban y con su mismo valor de `action`.
--
-- Por que no se quita la restriccion del todo
-- -------------------------------------------
-- Porque entonces cualquier cadena entraria y la columna dejaria de servir para
-- agrupar. Se amplia a los verbos que el codigo escribe de verdad -- los tres
-- del CRUD mas los que usaban los tres llamadores de `audit_event` -- y se deja
-- `custom` para lo que no encaje, de modo que un caso nuevo tenga donde caer
-- sin que haya que migrar otra vez.

BEGIN;

ALTER TABLE event_log DROP CONSTRAINT IF EXISTS event_log_action_check;

ALTER TABLE event_log ADD CONSTRAINT event_log_action_check CHECK (
    action IN (
        -- Los de siempre, que escribe `base_service`.
        'create', 'update', 'delete',
        -- Lectura: la comprobacion de permiso tambien la registra, y era uno de
        -- los verbos que no cabian.
        'read',
        -- Lo que no es un CRUD y por eso necesitaba otra tabla.
        'denied', 'transition', 'custom'
    )
);

-- `event_log` no decia de quien era el asiento mas alla del usuario. La
-- bitacora del restaurante si lo necesitaba -- filtraba por proyecto -- y lo
-- guardaba dentro de su JSON. Se sube a columna para poder filtrar sin abrir el
-- JSON en cada consulta.
ALTER TABLE event_log
    ADD COLUMN IF NOT EXISTS id_proyect INTEGER REFERENCES proyect(id_proyect);

CREATE INDEX IF NOT EXISTS idx_event_log_proyect
    ON event_log (id_proyect, creation_date);

-- El verbo concreto -- "cerrado", "mesa_cobrada" -- no cabe en `action`, que
-- ahora es la categoria. Va en su propia columna para que se pueda leer y
-- agrupar sin desarmar el JSON.
ALTER TABLE event_log
    ADD COLUMN IF NOT EXISTS event_detail VARCHAR(80);

DROP TABLE IF EXISTS audit_log;

COMMIT;
