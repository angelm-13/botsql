-- Registro de asistencias: cada checada guardada en la base.
--
-- De que se parte
-- ---------------
-- La pantalla de Asistencias (`/kronos`) le pregunta al checador Hikvision en
-- vivo y pinta lo que contesta, pero no guarda nada: cerrar la pantalla, que el
-- equipo se reinicie o que borre su memoria era perder las checadas. Sin ellas
-- en la base, la nomina no tiene de donde contar dias ni horas.
--
-- Que se agrega
-- -------------
-- `attendance_record`: una fila por checada (no por dia). El resumen por dia
-- -primera entrada, ultima salida, numero de marcas- se sigue calculando con
-- `summarize_attendance` (kronos_service.py), ahora sobre lo guardado; no se
-- guarda un segundo resumen que pudiera contradecir al primero.
--
--   id_user        el empleado del sistema, cuando se sepa cual es. Nulo por
--                  ahora: ligar el numero del checador con `user` es la
--                  siguiente fase.
--   employee_no    el numero de empleado tal como lo trae el checador.
--   employee_name  el nombre que trae el checador, para leer sin ligar.
--   check_time     hora de pared del negocio, sin zona (convencion de
--                  app/utils/tiempo.py para fechas que captura un dispositivo).
--   source         de donde vino: 'kronos' hoy; 'whatsapp' y 'manual' quedan
--                  permitidas desde ya para no tener que volver a tocar este
--                  CHECK cuando lleguen (reescribir un CHECK en una migracion
--                  que se reaplica en cada arranque ya trono dos veces).
--   source_ref     identificador de la checada en su origen. Para Kronos:
--                  `<host del equipo>:<serialNo del evento>`. Con UNIQUE
--                  (source, source_ref) importar dos veces el mismo rango no
--                  duplica nada.
--   door_no / verify_mode   puerta y forma de verificacion (huella, rostro).
--
-- Reaplicable: solo CREATE ... IF NOT EXISTS. No toca entity_permission; los
-- permisos llegan por la resiembra 20261016100100.
BEGIN;

CREATE TABLE IF NOT EXISTS attendance_record (
    id_attendance_record SERIAL PRIMARY KEY,
    id_user INTEGER NULL REFERENCES "user"(id_user) DEFERRABLE INITIALLY DEFERRED,
    employee_no VARCHAR(32) NOT NULL,
    employee_name VARCHAR(96) NULL,
    check_time TIMESTAMP NOT NULL,
    source VARCHAR(20) NOT NULL DEFAULT 'kronos'
        CONSTRAINT ck_attendance_record_source CHECK (source IN ('kronos', 'whatsapp', 'manual')),
    source_ref VARCHAR(64) NOT NULL,
    door_no VARCHAR(16) NULL,
    verify_mode VARCHAR(40) NULL,
    created_by INTEGER NOT NULL,
    creation_date TIMESTAMP NOT NULL DEFAULT now(),
    last_update_date TIMESTAMP NOT NULL DEFAULT now(),
    deletion_date TIMESTAMP NULL,
    CONSTRAINT uq_attendance_record_source_ref UNIQUE (source, source_ref)
);

CREATE INDEX IF NOT EXISTS ix_attendance_record_check_time
    ON attendance_record (check_time);
CREATE INDEX IF NOT EXISTS ix_attendance_record_employee_time
    ON attendance_record (employee_no, check_time);
CREATE INDEX IF NOT EXISTS ix_attendance_record_user
    ON attendance_record (id_user);

COMMIT;
