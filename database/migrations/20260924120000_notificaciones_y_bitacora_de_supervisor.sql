-- Notificaciones de proyecto + bitacora diaria del supervisor.
--
-- Por que
-- -------
-- Pedido de negocio (2026-09-24): que el lider del proyecto (rol de negocio
-- "Supervisor", columna `proyect.leader`) se entere cuando cambia el status
-- de un proyecto suyo, y que el Jefe de taller que lo tiene tomado
-- (`proyect.id_supervisor`) se entere si ese lider modifica el proyecto
-- mientras ya esta en produccion -- para decidir si la modificacion alcanza a
-- hacerse o es una correccion aparte. Ademas, reemplazar la bitacora de
-- actividades que hoy se entrega en Word por un registro dentro de TYAKXA,
-- con recordatorio automatico si un dia no se captura nada.
--
-- No hay tabla de notificaciones ni de bitacora de actividad hasta hoy. El
-- enganche real (que evento de `proyect_event` genera que notificacion, y el
-- job que revisa la bitacora faltante) vive en codigo Python
-- (`project_management_service.py`, `backend/app/jobs/tasks_notifications.py`)
-- -- esta migracion solo crea el esquema donde escriben.
--
-- `notification` no lleva `deletion_date`: no se retira logico, se marca
-- leida (`read_at`) y con eso basta -- no hay ningun flujo que la borre.
BEGIN;

CREATE TABLE IF NOT EXISTS notification (
    id_notification   SERIAL PRIMARY KEY,
    -- El destinatario. Nunca se lista "de todos" -- una notificacion es del
    -- usuario que la recibe, no un dato de negocio compartido.
    id_user           INTEGER NOT NULL REFERENCES "user"(id_user),
    id_proyect        INTEGER REFERENCES proyect(id_proyect),
    id_proyect_event  INTEGER REFERENCES proyect_event(id_proyect_event),
    notification_type VARCHAR(40) NOT NULL,
    title             VARCHAR(160) NOT NULL,
    content           TEXT,
    read_at           TIMESTAMP,
    created_by        INTEGER NOT NULL DEFAULT 1,
    creation_date     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_notification_user_unread
    ON notification (id_user) WHERE read_at IS NULL;

CREATE TABLE IF NOT EXISTS supervisor_activity_log (
    id_supervisor_activity_log SERIAL PRIMARY KEY,
    -- Quien captura. No necesariamente el rol de negocio "Supervisor" --
    -- cualquiera con el permiso puede llevar su bitacora --, pero es a quien
    -- se le reclama si falta un dia.
    id_user           INTEGER NOT NULL REFERENCES "user"(id_user),
    activity_date     DATE NOT NULL,
    content           TEXT NOT NULL,
    id_proyect        INTEGER REFERENCES proyect(id_proyect),
    created_by        INTEGER NOT NULL,
    creation_date     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_update_date  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deletion_date     TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_supervisor_activity_log_user_date
    ON supervisor_activity_log (id_user, activity_date) WHERE deletion_date IS NULL;

COMMIT;
