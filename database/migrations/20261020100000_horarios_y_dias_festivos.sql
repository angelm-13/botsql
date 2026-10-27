-- Horarios de trabajo, su asignacion a empleados y dias festivos.
--
-- De que se parte
-- ---------------
-- Asistencias guarda las checadas (`attendance_record`) y sabe de quien es cada
-- una (`attendance_employee_link`), pero no sabia a que hora le tocaba entrar a
-- cada empleado ni que dias trabaja. Sin eso no se pueden detectar retardos ni
-- faltas, y la nomina solo podia pagar los dias con checada: dejaba fuera los
-- dias de descanso y los festivos, que por ley tambien se pagan.
--
-- Que se agrega
-- -------------
-- work_schedule       un horario con nombre y minutos de tolerancia (10 por
--                     omision, decision de RH 2026-10-20).
-- work_schedule_day   que dias se trabaja y de que hora a que hora (weekday:
--                     0 lunes ... 6 domingo). El dia que no aparece es descanso.
-- employee_schedule   que horario tiene cada empleado, con vigencia
--                     (valid_to nulo = sin fin). Guarda el historial de turnos.
-- payroll_holiday     dias de descanso obligatorio (LFT art. 74). Se siembran
--                     los de 2026; RH agrega los de cada año.
--
-- Son tablas propias de RH y no las de disponibilidad de la agenda de citas
-- (calendar_profile / availability_rule), que son del CRM y tienen otro fin.
--
-- Reaplicable: CREATE ... IF NOT EXISTS y los festivos entran con
-- ON CONFLICT DO NOTHING. No toca entity_permission (los permisos llegan por la
-- resiembra 20261020100100).
BEGIN;

CREATE TABLE IF NOT EXISTS work_schedule (
    id_work_schedule SERIAL PRIMARY KEY,
    schedule_name VARCHAR(120) NOT NULL,
    tolerance_minutes INTEGER NOT NULL DEFAULT 10
        CONSTRAINT ck_work_schedule_tolerance CHECK (tolerance_minutes BETWEEN 0 AND 240),
    created_by INTEGER NOT NULL DEFAULT 1,
    creation_date TIMESTAMP NOT NULL DEFAULT now(),
    last_update_date TIMESTAMP NOT NULL DEFAULT now(),
    deletion_date TIMESTAMP NULL
);

CREATE TABLE IF NOT EXISTS work_schedule_day (
    id_work_schedule_day SERIAL PRIMARY KEY,
    id_work_schedule INTEGER NOT NULL REFERENCES work_schedule(id_work_schedule) DEFERRABLE INITIALLY DEFERRED,
    weekday INTEGER NOT NULL CONSTRAINT ck_work_schedule_day_weekday CHECK (weekday BETWEEN 0 AND 6),
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    created_by INTEGER NOT NULL DEFAULT 1,
    creation_date TIMESTAMP NOT NULL DEFAULT now(),
    last_update_date TIMESTAMP NOT NULL DEFAULT now(),
    deletion_date TIMESTAMP NULL,
    CONSTRAINT ck_work_schedule_day_hours CHECK (end_time > start_time)
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_work_schedule_day_vivo
    ON work_schedule_day (id_work_schedule, weekday) WHERE deletion_date IS NULL;

CREATE TABLE IF NOT EXISTS employee_schedule (
    id_employee_schedule SERIAL PRIMARY KEY,
    id_user INTEGER NOT NULL REFERENCES "user"(id_user) DEFERRABLE INITIALLY DEFERRED,
    id_work_schedule INTEGER NOT NULL REFERENCES work_schedule(id_work_schedule) DEFERRABLE INITIALLY DEFERRED,
    valid_from DATE NOT NULL,
    valid_to DATE NULL,
    created_by INTEGER NOT NULL DEFAULT 1,
    creation_date TIMESTAMP NOT NULL DEFAULT now(),
    last_update_date TIMESTAMP NOT NULL DEFAULT now(),
    deletion_date TIMESTAMP NULL,
    CONSTRAINT ck_employee_schedule_dates CHECK (valid_to IS NULL OR valid_to >= valid_from)
);
CREATE INDEX IF NOT EXISTS ix_employee_schedule_user ON employee_schedule (id_user);

CREATE TABLE IF NOT EXISTS payroll_holiday (
    id_payroll_holiday SERIAL PRIMARY KEY,
    holiday_date DATE NOT NULL,
    description VARCHAR(150) NOT NULL,
    source VARCHAR(200) NULL,
    created_by INTEGER NOT NULL DEFAULT 1,
    creation_date TIMESTAMP NOT NULL DEFAULT now(),
    last_update_date TIMESTAMP NOT NULL DEFAULT now(),
    deletion_date TIMESTAMP NULL,
    CONSTRAINT uq_payroll_holiday_date UNIQUE (holiday_date)
);

INSERT INTO payroll_holiday (holiday_date, description, source) VALUES
    (DATE '2026-01-01', 'Año nuevo', 'Ley Federal del Trabajo, art. 74 fr. I'),
    (DATE '2026-02-02', 'Día de la Constitución (primer lunes de febrero)', 'Ley Federal del Trabajo, art. 74 fr. II'),
    (DATE '2026-03-16', 'Natalicio de Benito Juárez (tercer lunes de marzo)', 'Ley Federal del Trabajo, art. 74 fr. III'),
    (DATE '2026-05-01', 'Día del Trabajo', 'Ley Federal del Trabajo, art. 74 fr. IV'),
    (DATE '2026-09-16', 'Día de la Independencia', 'Ley Federal del Trabajo, art. 74 fr. V'),
    (DATE '2026-11-16', 'Revolución Mexicana (tercer lunes de noviembre)', 'Ley Federal del Trabajo, art. 74 fr. VI'),
    (DATE '2026-12-25', 'Navidad', 'Ley Federal del Trabajo, art. 74 fr. VIII')
ON CONFLICT (holiday_date) DO NOTHING;

-- Faltas del periodo en el detalle de nomina (las cuenta el calculo; ver
-- payroll_calculation_service.py). `days_worked` pasa a ser "dias pagados".
ALTER TABLE payroll_detail
    ADD COLUMN IF NOT EXISTS absences INTEGER NULL;

COMMIT;
