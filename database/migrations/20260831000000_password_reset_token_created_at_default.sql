-- El DEFAULT de password_reset_token.created_at quedo como el string literal
-- 'datetime.now()' (codigo Python pegado por error, no una expresion SQL) en
-- 20260817020100_init_schema.sql y en database/init.sql. No se corrige ahi
-- directamente: ese archivo ya se aplico en tyakxa-dev/torredigital-prod/
-- adser-prod, y apply_migrations.py detiene TODO el proceso si el contenido
-- de una migracion ya aplicada cambia (compara checksum). Se corrige aqui,
-- en una migracion nueva, con un ALTER que corre sobre la tabla ya creada
-- (con el default viejo) tanto en bases existentes como en instalaciones
-- nuevas que acaban de correr esa migracion vieja.

BEGIN;

ALTER TABLE password_reset_token
    ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP;

COMMIT;
