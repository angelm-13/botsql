-- Quien participo en la bitacora del dia, de la plantilla del Jefe de taller.
--
-- Pedido de negocio explicito (2026-09-28): los obreros son usuarios sin rol
-- operativo (no se crea un rol nuevo para ellos); el Jefe de taller ya los
-- agrupa en un `team`/`nm_team_user` (el mismo mecanismo de equipos que ya
-- existe, ver 20260914110000_equipos_y_alcance_por_accion.sql) y selecciona,
-- para CADA bitacora, cuales de su plantilla trabajaron ese dia -- no todos
-- los dias participa todo el equipo.
--
-- Tabla puente aparte de `supervisor_activity_log` y no una columna JSON: se
-- necesita poder contar/filtrar por obrero despues (cuantos dias trabajo
-- fulano), y eso no se hace bien contra un campo de texto libre.
BEGIN;

CREATE TABLE IF NOT EXISTS activity_log_worker (
    id_activity_log_worker  SERIAL PRIMARY KEY,
    id_activity             INTEGER NOT NULL REFERENCES supervisor_activity_log(id_activity),
    id_user                 INTEGER NOT NULL REFERENCES "user"(id_user),
    created_by              INTEGER NOT NULL DEFAULT 1,
    creation_date           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deletion_date           TIMESTAMP,
    CONSTRAINT uq_activity_log_worker UNIQUE (id_activity, id_user)
);

CREATE INDEX IF NOT EXISTS idx_activity_log_worker_activity
    ON activity_log_worker (id_activity) WHERE deletion_date IS NULL;

CREATE INDEX IF NOT EXISTS idx_activity_log_worker_user
    ON activity_log_worker (id_user) WHERE deletion_date IS NULL;

COMMIT;
