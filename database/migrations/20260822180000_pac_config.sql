BEGIN;

CREATE TABLE IF NOT EXISTS pac_config (
    id_pac_config INTEGER PRIMARY KEY DEFAULT 1 CHECK (id_pac_config = 1),
    provider VARCHAR(40) NOT NULL DEFAULT 'fake' CHECK (provider IN ('fake', 'facturama_sandbox', 'facturama')),
    facturama_username VARCHAR(255),
    facturama_password_cipher BYTEA,
    facturama_password_nonce BYTEA,
    facturama_base_url VARCHAR(255),
    expedition_place VARCHAR(5),
    name_id VARCHAR(10) NOT NULL DEFAULT '1',
    last_update_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO pac_config (id_pac_config, provider)
VALUES (1, 'fake')
ON CONFLICT (id_pac_config) DO NOTHING;

COMMIT;