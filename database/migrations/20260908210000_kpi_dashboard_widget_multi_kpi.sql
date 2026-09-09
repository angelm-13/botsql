-- Un kpi_dashboard_widget ahora puede representar varios KPIs a la vez, no
-- solo uno: kpi_dashboard_widget_kpi es la tabla puente entre widget y KPI,
-- con el orden en que se muestran dentro del widget. Se copia el
-- id_kpi_definition que ya tenia cada widget existente (orden=100, el mismo
-- default de la columna) y luego se quita la columna vieja de
-- kpi_dashboard_widget -- no hay datos de produccion todavia, asi que no
-- hace falta mantenerla en paralelo.

BEGIN;

CREATE TABLE IF NOT EXISTS "kpi_dashboard_widget_kpi" (
  "id_kpi_dashboard_widget_kpi" SERIAL PRIMARY KEY,
  "id_kpi_dashboard_widget" INTEGER NOT NULL REFERENCES "kpi_dashboard_widget"("id_kpi_dashboard_widget"),
  "id_kpi_definition" INTEGER NOT NULL REFERENCES "kpi_definition"("id_kpi_definition"),
  "orden" INTEGER NOT NULL DEFAULT 100,
  CONSTRAINT "uq_kpi_dashboard_widget_kpi" UNIQUE ("id_kpi_dashboard_widget", "id_kpi_definition")
);

CREATE INDEX IF NOT EXISTS "idx_kpi_dashboard_widget_kpi_widget" ON "kpi_dashboard_widget_kpi" ("id_kpi_dashboard_widget");
CREATE INDEX IF NOT EXISTS "idx_kpi_dashboard_widget_kpi_definition" ON "kpi_dashboard_widget_kpi" ("id_kpi_definition");

-- Copiar el KPI que ya tenia cada widget existente, antes de quitar la
-- columna vieja.
--
-- Envuelto en un IF porque `db-migrate` re-aplica TODAS las migraciones en cada
-- arranque -no lleva tabla de control-, y en la segunda pasada la columna ya no
-- esta: este SELECT reventaba con
--
--     ERROR: column "id_kpi_definition" does not exist
--     DETAIL: There is a column named "id_kpi_definition" in table
--             "kpi_dashboard_widget_kpi", but it cannot be referenced from
--             this part of the query.
--
-- y con ON_ERROR_STOP=1 tumbaba el arranque entero (exit 3). El relleno solo
-- tiene sentido la primera vez, cuando la columna vieja aun existe.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'kpi_dashboard_widget'
          AND column_name = 'id_kpi_definition'
    ) THEN
        INSERT INTO "kpi_dashboard_widget_kpi"
            ("id_kpi_dashboard_widget", "id_kpi_definition", "orden")
        SELECT "id_kpi_dashboard_widget", "id_kpi_definition", 100
        FROM "kpi_dashboard_widget"
        WHERE "id_kpi_definition" IS NOT NULL
        ON CONFLICT ("id_kpi_dashboard_widget", "id_kpi_definition") DO NOTHING;
    END IF;
END $$;

ALTER TABLE "kpi_dashboard_widget" DROP CONSTRAINT IF EXISTS "kpi_dashboard_widget_id_kpi_definition_fkey";
DROP INDEX IF EXISTS "idx_kpi_dashboard_widget_definition";
ALTER TABLE "kpi_dashboard_widget" DROP COLUMN IF EXISTS "id_kpi_definition";

COMMIT;
