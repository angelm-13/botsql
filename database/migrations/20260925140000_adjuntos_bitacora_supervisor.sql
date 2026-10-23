-- Adjuntos de la bitácora diaria del supervisor.
--
-- `supervisor_activity_log` lleva solo texto (`content`). Para las fotos y
-- documentos de la jornada se necesita una tabla aparte: un .docx de lo
-- realizado, un .txt con notas, imagenes del trabajo en piso. Pueden ser
-- varios adjuntos por día, y a veces cero (error que dispara recordatorio
-- automático si falta).
--
-- La tabla NO es la bitacora en si, es solo los archivos que la acompañan.
-- El `activity_log` sigue siendo donde va el resumen que alguien escribe
-- ("Soldado parte A, esperando material para parte B").

BEGIN;

CREATE TABLE IF NOT EXISTS supervisor_daily_attachment (
    id_supervisor_daily_attachment SERIAL PRIMARY KEY,
    -- La bitacora del dia a la que pertenece (la FK al proyecto vive ahi).
    id_supervisor_activity_log INTEGER NOT NULL
        REFERENCES supervisor_activity_log(id_supervisor_activity_log),
    -- Fecha para búsqueda rápida (denormalización: ya está en activity_log,
    -- pero repeatirla acá acelera queries como "muestrame todos los adjuntos
    -- del proyecto X entre fechas Y-Z").
    attachment_date DATE NOT NULL,
    -- Ruta dentro de /uploads/supervisor_daily/YYYY/MM/DD/ o similar.
    file_path VARCHAR(400) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    extension VARCHAR(10) NOT NULL,
    mime_type VARCHAR(120) NOT NULL,
    file_size INTEGER NOT NULL,
    sha256 VARCHAR(64) NOT NULL,
    -- Descripcion opcional: "Foto de soldado", "Notas del dia", etc.
    description TEXT,
    created_by INTEGER NOT NULL DEFAULT 1,
    creation_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_update_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deletion_date TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_supervisor_daily_attachment_activity_log
    ON supervisor_daily_attachment(id_supervisor_activity_log) WHERE deletion_date IS NULL;

CREATE INDEX IF NOT EXISTS idx_supervisor_daily_attachment_date
    ON supervisor_daily_attachment(attachment_date) WHERE deletion_date IS NULL;

-- Para búsquedas "todos los adjuntos del proyecto X en un rango de fechas":
-- sin este índice, la query atraviesa supervisor_activity_log por cada fila
-- de supervisor_daily_attachment.
CREATE INDEX IF NOT EXISTS idx_supervisor_daily_attachment_proyect_date
    ON supervisor_daily_attachment(attachment_date)
    WHERE deletion_date IS NULL;

COMMIT;
