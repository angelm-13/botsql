-- Tablas de ISR y parametros de nomina, con las cifras oficiales de 2026.
--
-- De que se parte
-- ---------------
-- El calculo de nomina (payroll_calculation_service.py) solo sacaba el sueldo
-- por dias trabajados; no descontaba ISR ni IMSS. Esas deducciones dependen de
-- cifras oficiales que cambian cada año (tarifas del ISR, UMA, salario minimo,
-- subsidio), asi que se guardan en la base y no en el codigo: RH o el contador
-- las actualizan sin programar.
--
-- Que se agrega
-- -------------
-- payroll_isr_bracket   la tarifa del ISR para retenciones por salarios
--                       (art. 96 LISR), un renglon por tramo: limite inferior,
--                       limite superior (nulo = en adelante), cuota fija y
--                       porcentaje sobre el excedente. `period_days` dice de que
--                       tabla es: 1 diaria, 7, 10, 15 y 30 mensual.
-- payroll_parameter     un valor con su vigencia (`valid_from`..`valid_to`, nulo
--                       = sin fin) y su fuente: UMA, salario minimo, subsidio,
--                       cuotas obreras del IMSS, aguinaldo y prima vacacional.
--
-- Valores iniciales (con su fuente en la columna `source`):
--   ISR: SAT, Anexo 8 de la RMF 2026 (DOF 28/12/2025).
--   UMA 2026 117.31 diaria / 3,566.22 mensual desde el 1/02/2026 (INEGI, DOF
--     09/01/2026); enero de 2026 usa la de 2025, 113.14 / 3,439.46.
--   Salario minimo general 2026: 315.04 (CONASAMI, DOF 09/12/2025).
--   Subsidio para el empleo: 15.02 % de la UMA mensual (15.59 % en enero) para
--     ingresos mensuales de hasta 11,492.66 (DOF 31/12/2025).
--   Cuotas obreras del IMSS: Ley del Seguro Social (arts. 25, 106, 107, 147,
--     168) y tope de 25 UMA (art. 28). Aguinaldo y prima vacacional: LFT.
-- Deben revisarse con el contador antes de usarse en una nomina real.
--
-- Reaplicable: CREATE ... IF NOT EXISTS y los valores entran con
-- ON CONFLICT DO NOTHING, asi que una cifra que RH ya corrigio no se pisa en el
-- siguiente arranque. No toca entity_permission (los permisos llegan por la
-- resiembra 20261016130100).
BEGIN;

CREATE TABLE IF NOT EXISTS payroll_isr_bracket (
    id_payroll_isr_bracket SERIAL PRIMARY KEY,
    period_days INTEGER NOT NULL,
    valid_year INTEGER NOT NULL,
    lower_limit NUMERIC(14, 2) NOT NULL,
    upper_limit NUMERIC(14, 2) NULL,
    fixed_fee NUMERIC(14, 2) NOT NULL,
    rate_pct NUMERIC(6, 3) NOT NULL,
    source VARCHAR(200) NULL,
    created_by INTEGER NOT NULL DEFAULT 1,
    creation_date TIMESTAMP NOT NULL DEFAULT now(),
    last_update_date TIMESTAMP NOT NULL DEFAULT now(),
    deletion_date TIMESTAMP NULL,
    CONSTRAINT uq_payroll_isr_bracket UNIQUE (period_days, valid_year, lower_limit)
);

CREATE TABLE IF NOT EXISTS payroll_parameter (
    id_payroll_parameter SERIAL PRIMARY KEY,
    parameter_key VARCHAR(40) NOT NULL,
    value NUMERIC(14, 4) NOT NULL,
    valid_from DATE NOT NULL,
    valid_to DATE NULL,
    source VARCHAR(200) NULL,
    created_by INTEGER NOT NULL DEFAULT 1,
    creation_date TIMESTAMP NOT NULL DEFAULT now(),
    last_update_date TIMESTAMP NOT NULL DEFAULT now(),
    deletion_date TIMESTAMP NULL,
    CONSTRAINT uq_payroll_parameter UNIQUE (parameter_key, valid_from)
);

INSERT INTO payroll_isr_bracket (period_days, valid_year, lower_limit, upper_limit, fixed_fee, rate_pct, source) VALUES
    (1, 2026, 0.01, 27.78, 0.00, 1.92, 'SAT, Anexo 8 de la RMF 2026 (DOF 28/12/2025)'),
    (1, 2026, 27.79, 235.81, 0.53, 6.40, 'SAT, Anexo 8 de la RMF 2026 (DOF 28/12/2025)'),
    (1, 2026, 235.82, 414.41, 13.85, 10.88, 'SAT, Anexo 8 de la RMF 2026 (DOF 28/12/2025)'),
    (1, 2026, 414.42, 481.73, 33.28, 16.00, 'SAT, Anexo 8 de la RMF 2026 (DOF 28/12/2025)'),
    (1, 2026, 481.74, 576.76, 44.05, 17.92, 'SAT, Anexo 8 de la RMF 2026 (DOF 28/12/2025)'),
    (1, 2026, 576.77, 1163.25, 61.08, 21.36, 'SAT, Anexo 8 de la RMF 2026 (DOF 28/12/2025)'),
    (1, 2026, 1163.26, 1833.44, 186.35, 23.52, 'SAT, Anexo 8 de la RMF 2026 (DOF 28/12/2025)'),
    (1, 2026, 1833.45, 3500.35, 343.98, 30.00, 'SAT, Anexo 8 de la RMF 2026 (DOF 28/12/2025)'),
    (1, 2026, 3500.36, 4667.13, 844.05, 32.00, 'SAT, Anexo 8 de la RMF 2026 (DOF 28/12/2025)'),
    (1, 2026, 4667.14, 14001.38, 1217.42, 34.00, 'SAT, Anexo 8 de la RMF 2026 (DOF 28/12/2025)'),
    (1, 2026, 14001.39, NULL, 4391.07, 35.00, 'SAT, Anexo 8 de la RMF 2026 (DOF 28/12/2025)'),
    (7, 2026, 0.01, 194.46, 0.00, 1.92, 'SAT, Anexo 8 de la RMF 2026 (DOF 28/12/2025)'),
    (7, 2026, 194.47, 1650.67, 3.71, 6.40, 'SAT, Anexo 8 de la RMF 2026 (DOF 28/12/2025)'),
    (7, 2026, 1650.68, 2900.87, 96.95, 10.88, 'SAT, Anexo 8 de la RMF 2026 (DOF 28/12/2025)'),
    (7, 2026, 2900.88, 3372.11, 232.96, 16.00, 'SAT, Anexo 8 de la RMF 2026 (DOF 28/12/2025)'),
    (7, 2026, 3372.12, 4037.32, 308.35, 17.92, 'SAT, Anexo 8 de la RMF 2026 (DOF 28/12/2025)'),
    (7, 2026, 4037.33, 8142.75, 427.56, 21.36, 'SAT, Anexo 8 de la RMF 2026 (DOF 28/12/2025)'),
    (7, 2026, 8142.76, 12834.08, 1304.45, 23.52, 'SAT, Anexo 8 de la RMF 2026 (DOF 28/12/2025)'),
    (7, 2026, 12834.09, 24502.45, 2407.86, 30.00, 'SAT, Anexo 8 de la RMF 2026 (DOF 28/12/2025)'),
    (7, 2026, 24502.46, 32669.91, 5908.35, 32.00, 'SAT, Anexo 8 de la RMF 2026 (DOF 28/12/2025)'),
    (7, 2026, 32669.92, 98009.66, 8521.94, 34.00, 'SAT, Anexo 8 de la RMF 2026 (DOF 28/12/2025)'),
    (7, 2026, 98009.67, NULL, 30737.49, 35.00, 'SAT, Anexo 8 de la RMF 2026 (DOF 28/12/2025)'),
    (10, 2026, 0.01, 277.80, 0.00, 1.92, 'SAT, Anexo 8 de la RMF 2026 (DOF 28/12/2025)'),
    (10, 2026, 277.81, 2358.10, 5.30, 6.40, 'SAT, Anexo 8 de la RMF 2026 (DOF 28/12/2025)'),
    (10, 2026, 2358.11, 4144.10, 138.50, 10.88, 'SAT, Anexo 8 de la RMF 2026 (DOF 28/12/2025)'),
    (10, 2026, 4144.11, 4817.30, 332.80, 16.00, 'SAT, Anexo 8 de la RMF 2026 (DOF 28/12/2025)'),
    (10, 2026, 4817.31, 5767.60, 440.50, 17.92, 'SAT, Anexo 8 de la RMF 2026 (DOF 28/12/2025)'),
    (10, 2026, 5767.61, 11632.50, 610.80, 21.36, 'SAT, Anexo 8 de la RMF 2026 (DOF 28/12/2025)'),
    (10, 2026, 11632.51, 18334.40, 1863.50, 23.52, 'SAT, Anexo 8 de la RMF 2026 (DOF 28/12/2025)'),
    (10, 2026, 18334.41, 35003.50, 3439.80, 30.00, 'SAT, Anexo 8 de la RMF 2026 (DOF 28/12/2025)'),
    (10, 2026, 35003.51, 46671.30, 8440.50, 32.00, 'SAT, Anexo 8 de la RMF 2026 (DOF 28/12/2025)'),
    (10, 2026, 46671.31, 140013.80, 12174.20, 34.00, 'SAT, Anexo 8 de la RMF 2026 (DOF 28/12/2025)'),
    (10, 2026, 140013.81, NULL, 43910.70, 35.00, 'SAT, Anexo 8 de la RMF 2026 (DOF 28/12/2025)'),
    (15, 2026, 0.01, 416.70, 0.00, 1.92, 'SAT, Anexo 8 de la RMF 2026 (DOF 28/12/2025)'),
    (15, 2026, 416.71, 3537.15, 7.95, 6.40, 'SAT, Anexo 8 de la RMF 2026 (DOF 28/12/2025)'),
    (15, 2026, 3537.16, 6216.15, 207.75, 10.88, 'SAT, Anexo 8 de la RMF 2026 (DOF 28/12/2025)'),
    (15, 2026, 6216.16, 7225.95, 499.20, 16.00, 'SAT, Anexo 8 de la RMF 2026 (DOF 28/12/2025)'),
    (15, 2026, 7225.96, 8651.40, 660.75, 17.92, 'SAT, Anexo 8 de la RMF 2026 (DOF 28/12/2025)'),
    (15, 2026, 8651.41, 17448.75, 916.20, 21.36, 'SAT, Anexo 8 de la RMF 2026 (DOF 28/12/2025)'),
    (15, 2026, 17448.76, 27501.60, 2795.25, 23.52, 'SAT, Anexo 8 de la RMF 2026 (DOF 28/12/2025)'),
    (15, 2026, 27501.61, 52505.25, 5159.70, 30.00, 'SAT, Anexo 8 de la RMF 2026 (DOF 28/12/2025)'),
    (15, 2026, 52505.26, 70006.95, 12660.75, 32.00, 'SAT, Anexo 8 de la RMF 2026 (DOF 28/12/2025)'),
    (15, 2026, 70006.96, 210020.70, 18261.30, 34.00, 'SAT, Anexo 8 de la RMF 2026 (DOF 28/12/2025)'),
    (15, 2026, 210020.71, NULL, 65866.05, 35.00, 'SAT, Anexo 8 de la RMF 2026 (DOF 28/12/2025)'),
    (30, 2026, 0.01, 844.59, 0.00, 1.92, 'SAT, Anexo 8 de la RMF 2026 (DOF 28/12/2025)'),
    (30, 2026, 844.60, 7168.51, 16.22, 6.40, 'SAT, Anexo 8 de la RMF 2026 (DOF 28/12/2025)'),
    (30, 2026, 7168.52, 12598.02, 420.95, 10.88, 'SAT, Anexo 8 de la RMF 2026 (DOF 28/12/2025)'),
    (30, 2026, 12598.03, 14644.64, 1011.68, 16.00, 'SAT, Anexo 8 de la RMF 2026 (DOF 28/12/2025)'),
    (30, 2026, 14644.65, 17533.64, 1339.14, 17.92, 'SAT, Anexo 8 de la RMF 2026 (DOF 28/12/2025)'),
    (30, 2026, 17533.65, 35362.83, 1856.84, 21.36, 'SAT, Anexo 8 de la RMF 2026 (DOF 28/12/2025)'),
    (30, 2026, 35362.84, 55736.68, 5665.16, 23.52, 'SAT, Anexo 8 de la RMF 2026 (DOF 28/12/2025)'),
    (30, 2026, 55736.69, 106410.50, 10457.09, 30.00, 'SAT, Anexo 8 de la RMF 2026 (DOF 28/12/2025)'),
    (30, 2026, 106410.51, 141880.66, 25659.23, 32.00, 'SAT, Anexo 8 de la RMF 2026 (DOF 28/12/2025)'),
    (30, 2026, 141880.67, 425641.99, 37009.69, 34.00, 'SAT, Anexo 8 de la RMF 2026 (DOF 28/12/2025)'),
    (30, 2026, 425642.00, NULL, 133488.54, 35.00, 'SAT, Anexo 8 de la RMF 2026 (DOF 28/12/2025)')
ON CONFLICT (period_days, valid_year, lower_limit) DO NOTHING;

INSERT INTO payroll_parameter (parameter_key, value, valid_from, valid_to, source) VALUES
    ('uma_daily', 113.14, DATE '2025-02-01', DATE '2026-01-31', 'INEGI, UMA 2025 (DOF 10/01/2025)'),
    ('uma_daily', 117.31, DATE '2026-02-01', DATE '2027-01-31', 'INEGI, UMA 2026 (DOF 09/01/2026)'),
    ('uma_monthly', 3439.46, DATE '2025-02-01', DATE '2026-01-31', 'INEGI, UMA 2025 (DOF 10/01/2025)'),
    ('uma_monthly', 3566.22, DATE '2026-02-01', DATE '2027-01-31', 'INEGI, UMA 2026 (DOF 09/01/2026)'),
    ('minimum_wage_daily', 315.04, DATE '2026-01-01', DATE '2026-12-31', 'CONASAMI, salario minimo general 2026 (DOF 09/12/2025)'),
    ('subsidy_pct', 15.59, DATE '2026-01-01', DATE '2026-01-31', 'Decreto del subsidio para el empleo (DOF 31/12/2025), porcentaje de enero 2026'),
    ('subsidy_pct', 15.02, DATE '2026-02-01', DATE '2026-12-31', 'Decreto del subsidio para el empleo (DOF 31/12/2025)'),
    ('subsidy_income_limit', 11492.66, DATE '2026-01-01', DATE '2026-12-31', 'Decreto del subsidio para el empleo (DOF 31/12/2025)'),
    ('imss_em_surplus_pct', 0.400, DATE '2026-01-01', NULL, 'Ley del Seguro Social, art. 106 fr. II (enfermedad y maternidad, excedente de 3 UMA)'),
    ('imss_em_cash_pct', 0.250, DATE '2026-01-01', NULL, 'Ley del Seguro Social, art. 107 (prestaciones en dinero)'),
    ('imss_em_pensioners_pct', 0.375, DATE '2026-01-01', NULL, 'Ley del Seguro Social, art. 25 (gastos medicos de pensionados)'),
    ('imss_iv_pct', 0.625, DATE '2026-01-01', NULL, 'Ley del Seguro Social, art. 147 (invalidez y vida)'),
    ('imss_cv_pct', 1.125, DATE '2026-01-01', NULL, 'Ley del Seguro Social, art. 168 fr. II (cesantia en edad avanzada y vejez)'),
    ('imss_surplus_umas', 3, DATE '2026-01-01', NULL, 'Ley del Seguro Social, art. 106 fr. II (umbral del excedente, en UMA)'),
    ('sbc_cap_umas', 25, DATE '2026-01-01', NULL, 'Ley del Seguro Social, art. 28 (tope del salario base de cotizacion, en UMA)'),
    ('aguinaldo_days', 15, DATE '2026-01-01', NULL, 'Ley Federal del Trabajo, art. 87'),
    ('vacation_premium_pct', 25, DATE '2026-01-01', NULL, 'Ley Federal del Trabajo, art. 80')
ON CONFLICT (parameter_key, valid_from) DO NOTHING;

COMMIT;
