-- Prestaciones que cada empresa activa (respuestas de RH, 2026-11-04): Infonavit,
-- Fonacot, caja de ahorro, prestamo y pension alimenticia. Son descuentos (no
-- cambian la base del ISR ni del IMSS) y existen siempre en el catalogo; la hoja de
-- nomina solo las ofrece si la empresa las activa en Cifras oficiales
-- (services/prestaciones.py). Codigos propios PR_... para no tocar conceptos que la
-- empresa ya tenga con esos nombres. Idempotente: no duplica ni pisa conceptos existentes.
BEGIN;

INSERT INTO payroll_concept (payroll_code, payroll_concept_description, type, is_taxable, is_imss, created_by)
SELECT v.codigo, v.descripcion, 'deduction', false, false, 1
FROM (VALUES
    ('PR_INFONAVIT', 'Crédito Infonavit'),
    ('PR_FONACOT', 'Crédito Fonacot'),
    ('PR_CAJA_AHORRO', 'Caja de ahorro'),
    ('PR_PRESTAMO', 'Préstamo de la empresa'),
    ('PR_PENSION_ALIM', 'Pensión alimenticia')
) AS v(codigo, descripcion)
WHERE NOT EXISTS (
    SELECT 1 FROM payroll_concept c WHERE c.payroll_code = v.codigo AND c.deletion_date IS NULL
);

COMMIT;
