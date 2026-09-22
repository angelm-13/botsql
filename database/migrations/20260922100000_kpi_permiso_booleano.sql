-- nm_permission_kpi.control_type era el bitmask CRUD legado
-- (create=1, read=2, update=4, delete=8), heredado del resto del sistema de
-- permisos sin que tuviera sentido aqui: un KPI no se "crea" ni se "edita",
-- solo se ve o no se ve. Se reemplaza por un booleano real.
--
-- Confirmado antes de escribir esta migracion: la tabla tenia 0 filas (no
-- hay datos reales que perder). `DROP COLUMN IF EXISTS` / `ADD COLUMN IF NOT
-- EXISTS` son ya idempotentes por si solos -- no hace falta guarda extra
-- como la del incidente de CIERRE_SENTINELA (ver ARQUITECTURA_TYAKXA_TNY.md
-- seccion 7.1): ninguna otra migracion referencia
-- nm_permission_kpi.control_type.

BEGIN;

ALTER TABLE "nm_permission_kpi" DROP COLUMN IF EXISTS "control_type";
ALTER TABLE "nm_permission_kpi" ADD COLUMN IF NOT EXISTS "puede_ver" BOOLEAN NOT NULL DEFAULT true;

COMMIT;
