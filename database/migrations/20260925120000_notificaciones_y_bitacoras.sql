-- Migración: Notificaciones y Bitácoras Diarias
-- Descripción: Crea tablas para notificaciones entre roles y registros de actividades diarias de supervisores
-- Fecha: 2026-09-25

-- Tabla: notification
-- Propósito: Registrar notificaciones entre usuarios (Supervisor, Gerente, Jefe Taller, Almacenista)
CREATE TABLE IF NOT EXISTS notification (
    id_notification SERIAL PRIMARY KEY,
    id_user_recipient INTEGER NOT NULL REFERENCES "user"(id_user),
    id_user_sender INTEGER REFERENCES "user"(id_user),
    id_proyect INTEGER REFERENCES proyect(id_proyect),
    notification_type VARCHAR(50) NOT NULL DEFAULT 'custom',
    title VARCHAR(200) NOT NULL,
    message TEXT,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    read_date TIMESTAMP NULL,
    metadata JSONB DEFAULT '{}',
    created_by INTEGER NOT NULL REFERENCES "user"(id_user),
    creation_date TIMESTAMP NOT NULL DEFAULT NOW(),
    last_update_date TIMESTAMP NOT NULL DEFAULT NOW(),
    deletion_date TIMESTAMP NULL,
    CONSTRAINT notification_type_check CHECK (
        notification_type IN (
            'project_status_change',
            'project_modified',
            'activity_log_created',
            'task_assigned',
            'material_confirmed',
            'custom'
        )
    )
);

-- Índices para notification
CREATE INDEX IF NOT EXISTS idx_notification_recipient ON notification(id_user_recipient);
CREATE INDEX IF NOT EXISTS idx_notification_proyect ON notification(id_proyect);
CREATE INDEX IF NOT EXISTS idx_notification_creation_date ON notification(creation_date DESC);
CREATE INDEX IF NOT EXISTS idx_notification_is_read ON notification(is_read);

-- Tabla: supervisor_activity_log
-- Propósito: Registrar actividades diarias de supervisores en proyectos
CREATE TABLE IF NOT EXISTS supervisor_activity_log (
    id_activity SERIAL PRIMARY KEY,
    id_proyect INTEGER NOT NULL REFERENCES proyect(id_proyect),
    id_supervisor INTEGER NOT NULL REFERENCES "user"(id_user),
    activity_date DATE NOT NULL,
    description TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    hours_spent NUMERIC(5,2),
    notes TEXT,
    created_by INTEGER NOT NULL REFERENCES "user"(id_user),
    creation_date TIMESTAMP NOT NULL DEFAULT NOW(),
    last_update_date TIMESTAMP NOT NULL DEFAULT NOW(),
    deletion_date TIMESTAMP NULL,
    CONSTRAINT activity_status_check CHECK (
        status IN ('pending', 'in_progress', 'completed')
    )
);

-- Índices para supervisor_activity_log
CREATE INDEX IF NOT EXISTS idx_activity_proyect ON supervisor_activity_log(id_proyect);
CREATE INDEX IF NOT EXISTS idx_activity_supervisor ON supervisor_activity_log(id_supervisor);
CREATE INDEX IF NOT EXISTS idx_activity_date ON supervisor_activity_log(activity_date DESC);
CREATE INDEX IF NOT EXISTS idx_activity_proyect_supervisor_date ON supervisor_activity_log(id_proyect, id_supervisor, activity_date);

-- Comentarios de tabla para documentación
COMMENT ON TABLE notification IS 'Notificaciones entre roles: Supervisor, Gerente, Jefe de Taller, Almacenista. Registra cambios de estatus de proyectos, creación de tareas, etc.';
COMMENT ON COLUMN notification.notification_type IS 'Tipo de notificación: project_status_change, project_modified, activity_log_created, task_assigned, material_confirmed, custom';
COMMENT ON COLUMN notification.metadata IS 'JSON con datos adicionales: {previous_status, new_status, document_url, reason, etc}';

COMMENT ON TABLE supervisor_activity_log IS 'Registro diario de actividades que los supervisores realizan en sus proyectos. Base para bitácoras y auditoría.';
COMMENT ON COLUMN supervisor_activity_log.activity_date IS 'Fecha de la actividad registrada (puede ser pasada si se registra con retraso)';
COMMENT ON COLUMN supervisor_activity_log.status IS 'Estado del registro: pending (sin completar), in_progress (en curso), completed (terminado)';
COMMENT ON COLUMN supervisor_activity_log.hours_spent IS 'Horas de trabajo dedicadas a la actividad (campo opcional)';
