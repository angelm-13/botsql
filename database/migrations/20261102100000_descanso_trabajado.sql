-- Descanso o festivo trabajado (resto de la Etapa C; decisiones de RH 2026-11-02).
--
-- De que se parte
-- ---------------
-- Las horas extra ya se autorizan y se verifican contra las checadas, pero
-- trabajar en el dia de descanso o en un festivo (LFT arts. 73 y 75: se paga el
-- doble ademas del dia) no tenia registro.
--
-- Que se agrega
-- -------------
-- overtime.kind   'overtime' (como hasta hoy) o 'rest_day': el descanso o
--                 festivo trabajado usa el mismo registro y el mismo flujo de
--                 autorizacion que las horas extra (services/overtime_service.py).
-- La prima dominical (LFT art. 71) no necesita tabla: se calcula de las checadas
-- de cada domingo; su porcentaje (25 por omision) vive en payroll_parameter
-- como sunday_premium_pct y no se siembra.
--
-- Reaplicable: ADD COLUMN IF NOT EXISTS y el CHECK con guarda.
BEGIN;

ALTER TABLE overtime
    ADD COLUMN IF NOT EXISTS kind VARCHAR(20) NOT NULL DEFAULT 'overtime';

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_overtime_kind') THEN
        ALTER TABLE overtime ADD CONSTRAINT ck_overtime_kind CHECK (kind IN ('overtime', 'rest_day'));
    END IF;
END $$;

COMMIT;
