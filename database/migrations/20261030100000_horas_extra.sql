-- Horas extra y minutos de comida del horario (Etapa C; decisiones de RH 2026-10-30).
--
-- De que se parte
-- ---------------
-- No habia forma de registrar ni pagar horas extra, y nada evitaba que alguien
-- se quedara de mas (o no checara salida) para cobrarlas sin autorizacion.
--
-- Que se agrega
-- -------------
-- overtime            horas extra de un empleado en un dia: autorizadas antes
--                     (authorized), tiempo no autorizado que se aprobo
--                     (detected) o capturadas por RH sin checadas (manual); si se
--                     pagan o se compensan con tiempo libre (solo comentario); y
--                     el periodo que las pago, fijado al cerrarlo. Lo que se paga
--                     se verifica contra las checadas (services/overtime_service.py).
-- work_schedule.meal_minutes   minutos de comida del horario (60 por omision): la
--                     jornada es de la entrada a la salida menos la comida, y de
--                     ella sale el precio de la hora extra.
--
-- Reaplicable: CREATE ... IF NOT EXISTS y ADD COLUMN IF NOT EXISTS. No toca
-- entity_permission (las rutas deciden: el supervisor del empleado o RH).
BEGIN;

ALTER TABLE work_schedule
    ADD COLUMN IF NOT EXISTS meal_minutes INTEGER NOT NULL DEFAULT 60;

CREATE TABLE IF NOT EXISTS overtime (
    id_overtime SERIAL PRIMARY KEY,
    id_user INTEGER NOT NULL REFERENCES "user"(id_user) DEFERRABLE INITIALLY DEFERRED,
    work_date DATE NOT NULL,
    minutes INTEGER NOT NULL CONSTRAINT ck_overtime_minutes CHECK (minutes > 0),
    origin VARCHAR(20) NOT NULL DEFAULT 'authorized'
        CONSTRAINT ck_overtime_origin CHECK (origin IN ('authorized', 'detected', 'manual')),
    settlement VARCHAR(20) NOT NULL DEFAULT 'pay'
        CONSTRAINT ck_overtime_settlement CHECK (settlement IN ('pay', 'compensate')),
    notes VARCHAR(300) NULL,
    id_payroll_period INTEGER NULL REFERENCES payroll_period(id_payroll_period) DEFERRABLE INITIALLY DEFERRED,
    created_by INTEGER NOT NULL DEFAULT 1,
    creation_date TIMESTAMP NOT NULL DEFAULT now(),
    last_update_date TIMESTAMP NOT NULL DEFAULT now(),
    deletion_date TIMESTAMP NULL
);
CREATE INDEX IF NOT EXISTS ix_overtime_user_date ON overtime (id_user, work_date);

COMMIT;
