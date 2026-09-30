-- Repara una instalacion que ya habia corrido la version VIEJA de la
-- migracion de prioridad/costo total (20260925140000_proyect_priority_and_
-- total_cost.sql, la que este mismo commit de initAlan sustituyo por
-- 20260925150000_prioridad_y_costo_total_de_proyecto.sql).
--
-- La version vieja dejaba `priority`/`total_cost` NOT NULL con DEFAULT
-- ('media' / 0). La version nueva las declara opcionales (sin NOT NULL, sin
-- DEFAULT) -- pero un ALTER TABLE ... ADD COLUMN IF NOT EXISTS no toca nada
-- si la columna ya existe, asi que una base que ya corrio la vieja se queda
-- con el NOT NULL de antes para siempre, sin que la migracion nueva lo note.
--
-- Sintoma real, reproducido: create_project (que desde este mismo cambio de
-- initAlan ya NO manda un valor por omision para priority/total_cost, los
-- deja en None cuando el formulario no los captura) truena con
-- NotNullViolation en priority en CUALQUIER alta de proyecto -- el modulo
-- completo de Operaciones quedaba inutilizable en cualquier base que ya
-- tuviera la version vieja de la columna, tyakxa-dev incluida.
--
-- El ALTER COLUMN ... DROP NOT NULL/DROP DEFAULT es un no-op seguro si la
-- columna ya esta como se quiere (una base nueva, sembrada solo con la
-- migracion nueva, nunca tuvo el NOT NULL de por si). Se puede correr las
-- veces que haga falta.
BEGIN;

ALTER TABLE proyect ALTER COLUMN priority DROP NOT NULL;
ALTER TABLE proyect ALTER COLUMN priority DROP DEFAULT;
ALTER TABLE proyect ALTER COLUMN total_cost DROP NOT NULL;
ALTER TABLE proyect ALTER COLUMN total_cost DROP DEFAULT;

COMMIT;
