-- RF-17: bitacora persistente de cada consulta al modulo BI (quien, con que rol, que pregunto,
-- que SQL se ejecuto, cuantas filas y cuanto tardo). Idempotente: corre en cada arranque.
CREATE TABLE IF NOT EXISTS bi_query_log (
    id_bi_query_log BIGSERIAL PRIMARY KEY,
    id_user         INTEGER,
    rol             VARCHAR(120),
    pregunta        VARCHAR(1000) NOT NULL,
    sql_ejecutado   TEXT,
    ok              BOOLEAN NOT NULL,
    http            SMALLINT,
    error_tipo      VARCHAR(80),
    filas           INTEGER,
    ms_total        INTEGER,
    desde_cache     BOOLEAN,
    creation_date   TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_bi_query_log_user_date ON bi_query_log (id_user, creation_date DESC);
