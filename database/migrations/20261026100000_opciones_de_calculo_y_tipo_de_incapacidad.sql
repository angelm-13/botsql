-- Opciones de calculo de nomina por empresa y tipo de incapacidad.
--
-- De que se parte
-- ---------------
-- La revision contable de la guia de calculo (2026-10-26) confirmo las reglas,
-- pero pidio que algunas decisiones las tome cada empresa, porque no todas lo
-- hacen igual. El calculo seguia una sola forma fija.
--
-- Que se agrega
-- -------------
-- payroll_parameter   tres opciones (1 = si, 0 = no), con vigencia y fuente como
--                     cualquier cifra, para que se vea desde cuando aplica cada
--                     politica:
--                       option_imss_on_absences     cotizar IMSS en dias de falta
--                       option_aguinaldo_discounts  descontar del aguinaldo las
--                                                   faltas injustificadas y las
--                                                   incapacidades por enfermedad
--                                                   general
--                       option_subsidy_month_days   subsidio con los dias reales
--                                                   del mes y no con 30.4
--                     Entran en 0: el calculo sigue igual que antes. La tabla de
--                     vacaciones de la empresa (vacation_days_*) no se siembra:
--                     sin capturar vale la de la ley.
-- employee_leave.disability_type   tipo de incapacidad: general_illness,
--                     work_risk o maternity. Solo la de enfermedad general puede
--                     bajar el aguinaldo; las otras dos nunca (LFT). Lo ya
--                     registrado queda sin tipo y no se descuenta.
--
-- Reaplicable: ADD COLUMN IF NOT EXISTS, el CHECK con guarda y las opciones con
-- ON CONFLICT DO NOTHING (si RH las cambia, no se vuelven a pisar). No toca
-- entity_permission (el catalogo de campos llega por la resiembra 20261026100100).
BEGIN;

ALTER TABLE employee_leave
    ADD COLUMN IF NOT EXISTS disability_type VARCHAR(20) NULL;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_employee_leave_disability_type') THEN
        ALTER TABLE employee_leave ADD CONSTRAINT ck_employee_leave_disability_type
            CHECK (disability_type IS NULL OR disability_type IN ('general_illness', 'work_risk', 'maternity'));
    END IF;
END $$;

INSERT INTO payroll_parameter (parameter_key, value, valid_from, valid_to, source) VALUES
    ('option_imss_on_absences', 0, DATE '2026-01-01', NULL, 'Politica de la empresa (LSS art. 31)'),
    ('option_aguinaldo_discounts', 0, DATE '2026-01-01', NULL, 'Politica de la empresa (LFT art. 87)'),
    ('option_subsidy_month_days', 0, DATE '2026-01-01', NULL, 'Politica de la empresa (decreto del subsidio para el empleo)')
ON CONFLICT (parameter_key, valid_from) DO NOTHING;

COMMIT;
