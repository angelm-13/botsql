-- Modulo de KPIs: catalogo de indicadores, permisos por indicador y
-- tableros personalizables por usuario.
--
-- Las cuatro entidades se registran en el modulo `kpis`
-- (backend/app/modules/registry.py) sin entrada propia en el menu lateral:
-- sus pantallas viven dentro del Home/Dashboard actual (ruta "/"), que ya es
-- de acceso libre para cualquier usuario autenticado. Por eso sus filas de
-- entity_permission se siembran con menu_location = 'hidden'.
--
-- `CREATE TABLE IF NOT EXISTS` en las cuatro, nunca una guarda basada solo en
-- deletion_date -- ver seccion 7.1 de ARQUITECTURA_TYAKXA_TNY.md sobre filas
-- fantasma en reinicios de pod: el initContainer de k8s corre esta cadena
-- completa en cada arranque.

BEGIN;

-- Catalogo de indicadores disponibles.
CREATE TABLE IF NOT EXISTS "kpi_definition" (
  "id_kpi_definition" SERIAL PRIMARY KEY,
  "clave" VARCHAR(80) NOT NULL UNIQUE,
  "etiqueta" VARCHAR(150) NOT NULL,
  "modulo" VARCHAR(40) NOT NULL,
  "dimensiones" JSONB NOT NULL DEFAULT '[]'::jsonb,
  "unidad" VARCHAR(20) NOT NULL DEFAULT 'numero',
  "created_by" INTEGER NOT NULL DEFAULT 1,
  "creation_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "last_update_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "deletion_date" TIMESTAMP NULL
);

-- Que perfil puede ver que indicador.
CREATE TABLE IF NOT EXISTS "nm_permission_kpi" (
  "id_nm_permission_kpi" SERIAL PRIMARY KEY,
  "id_permission" INTEGER NOT NULL,
  "id_kpi_definition" INTEGER NOT NULL REFERENCES "kpi_definition"("id_kpi_definition"),
  "control_type" SMALLINT NOT NULL DEFAULT 2,
  "created_by" INTEGER NOT NULL DEFAULT 1,
  "creation_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "last_update_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "deletion_date" TIMESTAMP NULL,
  CONSTRAINT "uq_nm_permission_kpi" UNIQUE ("id_permission", "id_kpi_definition")
);

CREATE INDEX IF NOT EXISTS "idx_nm_permission_kpi_permission" ON "nm_permission_kpi" ("id_permission");
CREATE INDEX IF NOT EXISTS "idx_nm_permission_kpi_definition" ON "nm_permission_kpi" ("id_kpi_definition");

-- Tablero personalizable por usuario.
CREATE TABLE IF NOT EXISTS "kpi_dashboard" (
  "id_kpi_dashboard" SERIAL PRIMARY KEY,
  "id_user" INTEGER NOT NULL,
  "nombre" VARCHAR(100) NOT NULL,
  "orden" INTEGER NOT NULL DEFAULT 100,
  "created_by" INTEGER NOT NULL DEFAULT 1,
  "creation_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "last_update_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "deletion_date" TIMESTAMP NULL
);

CREATE INDEX IF NOT EXISTS "idx_kpi_dashboard_user" ON "kpi_dashboard" ("id_user");

-- Cada grafica dentro de un tablero.
CREATE TABLE IF NOT EXISTS "kpi_dashboard_widget" (
  "id_kpi_dashboard_widget" SERIAL PRIMARY KEY,
  "id_kpi_dashboard" INTEGER NOT NULL REFERENCES "kpi_dashboard"("id_kpi_dashboard"),
  "id_kpi_definition" INTEGER NOT NULL REFERENCES "kpi_definition"("id_kpi_definition"),
  "tipo_grafica" VARCHAR(30) NOT NULL,
  "parametros" JSONB NOT NULL DEFAULT '{}'::jsonb,
  "posicion_orden" INTEGER NOT NULL DEFAULT 100,
  "creation_date" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "deletion_date" TIMESTAMP NULL
);

CREATE INDEX IF NOT EXISTS "idx_kpi_dashboard_widget_dashboard" ON "kpi_dashboard_widget" ("id_kpi_dashboard");
-- El indice, solo si la columna todavia existe.
--
-- `db-migrate` re-aplica TODAS las migraciones en cada arranque -no lleva tabla
-- de control-, asi que cada una tiene que poder correr dos veces. Y esta no
-- podia: 20260908210000 movio los KPIs de un widget a su propia tabla y quito
-- `id_kpi_definition` de `kpi_dashboard_widget`, asi que en la segunda pasada
-- este CREATE INDEX revienta con
--
--     ERROR: column "id_kpi_definition" does not exist
--
-- y con ON_ERROR_STOP=1 tumba el arranque entero: `docker compose up` sale con
-- exit 3 y el sistema no levanta. El CREATE TABLE de arriba no lo nota porque
-- es IF NOT EXISTS; el indice no tiene esa salida.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'kpi_dashboard_widget'
          AND column_name = 'id_kpi_definition'
    ) THEN
        CREATE INDEX IF NOT EXISTS "idx_kpi_dashboard_widget_definition"
            ON "kpi_dashboard_widget" ("id_kpi_definition");
    END IF;
END $$;

COMMIT;
