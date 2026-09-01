BEGIN;

-- Amplia el CHECK de pac_config.provider para el modo multiemisor: misma
-- cuenta compartida de Facturama, pero timbrando con un nodo "Issuer" propio
-- por RFC via el endpoint api-lite (ver backend/app/services/stamping.py,
-- FacturamaMultiemisorProvider). No se convierte pac_config en una fila por
-- empresa -- sigue siendo cuenta unica, igual que en cotizador_demo.
ALTER TABLE pac_config DROP CONSTRAINT IF EXISTS pac_config_provider_check;
ALTER TABLE pac_config ADD CONSTRAINT pac_config_provider_check
    CHECK (provider IN ('fake', 'facturama_sandbox', 'facturama',
                         'facturama_multiemisor_sandbox', 'facturama_multiemisor'));

-- Estatus del CSD por RFC. Antes no habia donde guardarlo: pac_config es una
-- sola cuenta, no una por emisor, asi que el CSD de un RFC concreto no tenia
-- fila propia hasta ahora.
ALTER TABLE customer_supplier
    ADD COLUMN IF NOT EXISTS csd_status VARCHAR(20) NOT NULL DEFAULT 'none'
        CHECK (csd_status IN ('none', 'uploaded', 'error')),
    ADD COLUMN IF NOT EXISTS csd_uploaded_at TIMESTAMP;

COMMIT;
