-- Cache diaria de KPIs, ya resuelta por dimension y periodo.
--
-- La llena `app.jobs.tasks_kpis.recalculate_kpi_snapshots` (Celery, corre de
-- madrugada) con upsert sobre (id_kpi_definition, dimension_key, periodo); no
-- se declara como entidad del modulo "kpis" en
-- backend/app/modules/registry.py porque nadie la lista ni la edita por CRUD
-- generico -- ver el comentario en app/models/kpi_snapshot.py.
--
-- `CREATE TABLE IF NOT EXISTS`, nunca una guarda basada solo en
-- deletion_date -- ver seccion 7.1 de ARQUITECTURA_TYAKXA_TNY.md.

BEGIN;

CREATE TABLE IF NOT EXISTS "kpi_snapshot" (
  "id_kpi_snapshot" BIGSERIAL PRIMARY KEY,
  "id_kpi_definition" INTEGER NOT NULL REFERENCES "kpi_definition"("id_kpi_definition"),
  "dimension_key" JSONB NOT NULL,
  "periodo" DATE NOT NULL,
  "valor" NUMERIC NOT NULL,
  "computed_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT "uq_kpi_snapshot_dia" UNIQUE ("id_kpi_definition", "dimension_key", "periodo")
);

CREATE INDEX IF NOT EXISTS "idx_kpi_snapshot_lookup" ON "kpi_snapshot" ("id_kpi_definition", "periodo");

COMMIT;
