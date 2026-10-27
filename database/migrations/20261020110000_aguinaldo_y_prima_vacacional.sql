-- Aguinaldo y prima vacacional en el calculo de nomina.
--
-- De que se parte
-- ---------------
-- El calculo ya usaba los dias de aguinaldo (15) y la prima vacacional (25 %)
-- solo para el factor de integracion del IMSS, pero nunca los pagaba.
--
-- Que se agrega
-- -------------
-- payroll_period.includes_aguinaldo   casilla del periodo: si esta marcada, el
--                                     calculo paga el aguinaldo (LFT art. 87).
--                                     La prima vacacional no necesita casilla:
--                                     se paga en el periodo donde cae el
--                                     aniversario de ingreso (LFT art. 80).
-- payroll_parameter                   topes exentos de ISR, en UMA (LISR art. 93
--                                     fr. XIV): 30 para el aguinaldo y 15 para
--                                     la prima vacacional. Lo que pase del tope
--                                     grava en el periodo.
--
-- Reaplicable: ADD COLUMN IF NOT EXISTS y los parametros entran con
-- ON CONFLICT DO NOTHING (si RH los corrige, no se vuelven a pisar). No toca
-- entity_permission (el catalogo de campos llega por la resiembra 20261020110100).
BEGIN;

ALTER TABLE payroll_period
    ADD COLUMN IF NOT EXISTS includes_aguinaldo boolean NOT NULL DEFAULT false;

INSERT INTO payroll_parameter (parameter_key, value, valid_from, valid_to, source) VALUES
    ('aguinaldo_exempt_umas', 30, DATE '2026-01-01', NULL, 'Ley del ISR, art. 93 fr. XIV (aguinaldo exento hasta 30 UMA)'),
    ('vacation_premium_exempt_umas', 15, DATE '2026-01-01', NULL, 'Ley del ISR, art. 93 fr. XIV (prima vacacional exenta hasta 15 UMA)')
ON CONFLICT (parameter_key, valid_from) DO NOTHING;

COMMIT;
