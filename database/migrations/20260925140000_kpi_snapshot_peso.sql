-- kpi_snapshot.peso: cuantos casos hay detras de un valor (tareas,
-- incidentes, ordenes), para que un porcentaje o un promedio se pueda
-- combinar entre dias y proyectos como promedio ponderado:
-- SUM(valor * peso) / SUM(peso).
--
-- Antes `_totales()` (backend/app/routes/kpi.py) sumaba siempre los
-- snapshots del rango, y eso inflaba cualquier KPI que no fuera un conteo o
-- un monto (medido contra Postgres real: 30 dias de un 50 % daban 1500 %).
-- Cada KPI declara ahora su regla en `agregacion` (backend/app/kpis/registry.py);
-- los de `promedio_ponderado` escriben aqui su peso.
--
-- Nullable a proposito: los KPIs de "suma"/"ultimo" no usan peso, y las filas
-- que ya existen no lo tienen. `_totales()` ignora las filas de un KPI
-- ponderado sin peso -- las que se escribieron antes de este cambio con la
-- forma vieja (un porcentaje del rango completo fechado en `fecha_fin`), que
-- no se pueden combinar bien; un backfill con `recalcular_kpi_snapshots_rango`
-- las reemplaza por las nuevas.
--
-- Idempotente: se reaplica en cada arranque (ver ARQUITECTURA_TYAKXA_TNY.md 7.1).

BEGIN;

ALTER TABLE "kpi_snapshot" ADD COLUMN IF NOT EXISTS "peso" NUMERIC;

COMMIT;
