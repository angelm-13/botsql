-- Precision fiscal de partidas CFDI 4.0 y soporte de IVA exento.
--
-- 1) El Anexo 20 permite hasta 6 decimales en Cantidad y ValorUnitario. Con
--    NUMERIC(10,2) un precio como 33.333 se truncaba a 33.33 y el SubTotal
--    guardado dejaba de cuadrar con el del XML timbrado (rechazo CFDI40129).
-- 2) TasaOCuota lleva 6 decimales (p. ej. retencion de IVA 0.106667); con
--    NUMERIC(7,4) se perdian las dos ultimas posiciones.
-- 3) iva_exempt distingue el IVA exento (TipoFactor="Exento", sin TasaOCuota
--    ni Importe) de la tasa 0% (TipoFactor="Tasa", TasaOCuota="0.000000"),
--    que el SAT trata como cosas distintas.

BEGIN;

-- Una vista posterior (`v_partidas`, del modulo asistente) puede depender de
-- estas columnas. Postgres no deja alterar el tipo de una columna que una
-- vista usa, ni siquiera si el tipo destino ya es el mismo -- asi que sin
-- este DROP, en cuanto esa vista existiera, esta migracion reaplicable
-- tronaria en cada arranque. Quien la cree despues (mas reciente por fecha
-- de archivo) la vuelve a dejar con `CREATE OR REPLACE VIEW` en el mismo
-- pase de migraciones.
DROP VIEW IF EXISTS v_partidas;

ALTER TABLE invoice_material_service
    ALTER COLUMN quantity TYPE NUMERIC(18, 6),
    ALTER COLUMN gross_price TYPE NUMERIC(18, 6),
    ALTER COLUMN tax_rate TYPE NUMERIC(9, 6),
    ALTER COLUMN isr_retention_rate TYPE NUMERIC(9, 6),
    ALTER COLUMN iva_retention_rate TYPE NUMERIC(9, 6);

ALTER TABLE invoice_material_service
    ADD COLUMN IF NOT EXISTS iva_exempt BOOLEAN NOT NULL DEFAULT FALSE;

COMMIT;
