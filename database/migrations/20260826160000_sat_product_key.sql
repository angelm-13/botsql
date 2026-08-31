-- Catalogo c_ClaveProdServ del SAT (unas 52,000 claves).
--
-- Sin esta tabla la captura de una factura obliga a teclear de memoria la clave
-- de 8 digitos de cada concepto, y el error se descubre hasta el timbrado.
-- Se llena con `backend/scripts/import_sat_catalog.py`.
--
-- Las columnas *_norm guardan la version en minusculas y sin acentos, que es
-- contra la que se busca: en espanol se teclea "consultoria" y el catalogo dice
-- "consultoria" con acento, y sin normalizar el LIKE no encuentra nada.

BEGIN;

CREATE TABLE IF NOT EXISTS sat_product_key (
    id_sat_product_key SERIAL PRIMARY KEY,
    clave VARCHAR(8) NOT NULL UNIQUE,
    description TEXT NOT NULL,
    keywords TEXT,
    description_norm TEXT,
    keywords_norm TEXT,
    creation_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_sat_product_key_clave
    ON sat_product_key (clave);
CREATE INDEX IF NOT EXISTS ix_sat_product_key_description_norm
    ON sat_product_key (description_norm);
CREATE INDEX IF NOT EXISTS ix_sat_product_key_keywords_norm
    ON sat_product_key (keywords_norm);

COMMIT;
