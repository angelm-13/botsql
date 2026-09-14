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

-- id_kpi_definition existe aqui solo en una instalacion nueva -- en
-- cualquiera que ya haya corrido 20260908210000_kpi_dashboard_widget_multi_kpi.sql
-- esa columna ya se elimino (paso a la tabla puente kpi_dashboard_widget_kpi).
-- Como el initContainer corre esta cadena completa en cada arranque (ver
-- encabezado del archivo), este CREATE INDEX sin guarda truena en el
-- segundo arranque en adelante con "column id_kpi_definition does not
-- exist" -- se vio real en tyakxa-dev.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'kpi_dashboard_widget' AND column_name = 'id_kpi_definition'
    ) THEN
        CREATE INDEX IF NOT EXISTS "idx_kpi_dashboard_widget_definition" ON "kpi_dashboard_widget" ("id_kpi_definition");
    END IF;
END $$;

COMMIT;
