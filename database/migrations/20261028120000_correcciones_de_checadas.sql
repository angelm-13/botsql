-- Correcciones de checadas con limite por mes.
--
-- De que se parte
-- ---------------
-- Una checada mal hecha o que faltaba (la salida) no tenia como corregirse con
-- control: o se dejaba mal o se editaba sin rastro. La revision contable
-- (2026-10-28) pidio que el supervisor pueda corregir, con limite, para evitar
-- que alguien "acomode" sus horas y para que cada quien se haga responsable.
--
-- Que se agrega
-- -------------
-- attendance_correction   cada hora corregida o agregada: la checada, el
--                     empleado, el dia, la hora de antes (nula si se agrego), la
--                     nueva, el motivo (obligatorio), si fue excepcion de RH y
--                     quien y cuando. La checada misma se corrige en
--                     attendance_record; aqui queda el historial.
-- El limite por mes (attendance_correction_limit, 2 por omision) vive en
-- payroll_parameter y no se siembra: sin capturar vale 2
-- (services/attendance_correction_service.py).
--
-- Reaplicable: CREATE ... IF NOT EXISTS. No toca entity_permission.
BEGIN;

CREATE TABLE IF NOT EXISTS attendance_correction (
    id_attendance_correction SERIAL PRIMARY KEY,
    id_attendance_record INTEGER NOT NULL REFERENCES attendance_record(id_attendance_record) DEFERRABLE INITIALLY DEFERRED,
    id_user INTEGER NOT NULL REFERENCES "user"(id_user) DEFERRABLE INITIALLY DEFERRED,
    check_date DATE NOT NULL,
    previous_time TIMESTAMP NULL,
    new_time TIMESTAMP NOT NULL,
    reason VARCHAR(300) NOT NULL,
    is_exception BOOLEAN NOT NULL DEFAULT false,
    created_by INTEGER NOT NULL DEFAULT 1,
    creation_date TIMESTAMP NOT NULL DEFAULT now(),
    last_update_date TIMESTAMP NOT NULL DEFAULT now(),
    deletion_date TIMESTAMP NULL
);
CREATE INDEX IF NOT EXISTS ix_attendance_correction_user_date ON attendance_correction (id_user, check_date);

COMMIT;
