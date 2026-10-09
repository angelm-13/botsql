-- XML timbrado de cada factura, guardado en la base.
--
-- Hasta ahora el XML vivia solo como archivo en /uploads/cfdi_xml. Sin volumen
-- persistente (torredigital-prod, antes del 2026-09-07) un reinicio del pod lo
-- borraba, y sin el XML el PDF de la factura sale sin QR, sin sello del emisor
-- y sin cadena original: todo eso se lee del XML. La tabla es aditiva; el
-- archivo sigue escribiendose como copia secundaria.
--
-- Se reaplica en cada arranque del pod (sin tabla de control, ver
-- ARQUITECTURA_TYAKXA_TNY.md 7.1): todo es IF NOT EXISTS. No toca
-- entity_permission ni ninguna columna scope_*. Las filas de facturas ya
-- existentes se cargan con backend/scripts/backfill_invoice_cfdi_xml.py, que
-- lee los archivos: SQL no puede.
BEGIN;

CREATE TABLE IF NOT EXISTS invoice_cfdi_xml (
    id_invoice INTEGER PRIMARY KEY REFERENCES invoice (id_invoice),
    xml TEXT NOT NULL,
    creation_date TIMESTAMP NOT NULL DEFAULT now(),
    last_update_date TIMESTAMP NOT NULL DEFAULT now()
);

COMMIT;
