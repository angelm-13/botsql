-- Simplifica Tarea y convierte "fase" de texto libre a un catalogo fijo.
--
-- Se retiran `leader` y `analyst`: enteros sueltos sin llave foranea (el
-- mismo defecto que ya tenian `dependency` y `validation`, que se quedan).
-- En produccion real nunca sirvieron para distinguir personas -- las 13
-- tareas reales de torredigital-prod comparten un solo valor en las tres,
-- el default de instalacion (1) que trae `20260817020100_init_schema.sql` --
-- y Jefe de taller/Supervisor pidieron simplificar la pantalla al minimo.
-- `owner` NO se toca aunque tenga el mismo defecto de fondo: ya alimenta el
-- KPI real "Desarrollo por empleado" (`desarrollo_por_empleado_query` en
-- app/kpis/registry.py), que agrupa por ese campo -- quitarlo dejaria ese
-- KPI sin poder distinguir responsables.
--
-- "fase" pasa de texto libre a los 5 valores que pidio Jefe de taller para el
-- tablero del taller (en_espera/en_proceso/bloqueado/terminado/entregado),
-- independiente de `task_status` -que ya tiene su propia maquina de estados
-- en operations_workflow.py- para no confundir el estatus formal de la tarea
-- con su columna visual en el tablero.
--
-- Corre en cada arranque del pod (ver
-- project_tyakxa_tny_migraciones_replay_infinito en memoria): el DROP COLUMN
-- usa IF EXISTS y el UPDATE de normalizacion es idempotente por construccion
-- -una fila ya llevada al catalogo no cambia al re-evaluarse-.

ALTER TABLE "task" DROP COLUMN IF EXISTS "leader";
ALTER TABLE "task" DROP COLUMN IF EXISTS "analyst";

-- Normaliza lo que ya habia antes del catalogo. Unicas variantes reales
-- vistas (tyakxa-dev, ambiente de bajo riesgo): "Ejecucion" y "Cierre" --
-- ver app/services/operations_workflow.py:TASK_FASE_ALIASES, que usa el
-- mismo criterio para lo que se capture desde ahora.
UPDATE "task"
   SET "fase" = 'en_proceso'
 WHERE lower(trim("fase")) IN ('ejecucion', 'ejecución');

UPDATE "task"
   SET "fase" = 'terminado'
 WHERE lower(trim("fase")) IN ('cierre');

-- Lo que no se reconoce se deja en NULL en vez de rechazarse o adivinar una
-- fase que no se sabe si es cierta -- igual de conservador que
-- `normalize_status` con task_status/incident_status.
UPDATE "task"
   SET "fase" = NULL
 WHERE "fase" IS NOT NULL
   AND "fase" NOT IN ('en_espera', 'en_proceso', 'bloqueado', 'terminado', 'entregado');
