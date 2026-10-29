-- Rol de base de datos de SOLO LECTURA para el modulo BI (tercera barrera tras el validador y
-- la transaccion de solo lectura). No va en database/migrations/ porque necesita una contrasena
-- que no debe vivir en el repositorio. Idempotente. Uso:
--   psql -U <superusuario> -d <base> -v pwd="'<contrasena>'" -f database/bi_lector.sql
-- y despues BI_DATABASE_URL=postgresql+psycopg2://bi_lector:<contrasena>@<host>:5432/<base>
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'bi_lector') THEN
        CREATE ROLE bi_lector LOGIN;
    END IF;
END $$;

ALTER ROLE bi_lector PASSWORD :pwd;
ALTER ROLE bi_lector SET default_transaction_read_only = on;
GRANT USAGE ON SCHEMA public TO bi_lector;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO bi_lector;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO bi_lector;
-- La bitacora y los secretos del propio ERP no los lee el modulo BI.
REVOKE ALL ON bi_query_log FROM bi_lector;
