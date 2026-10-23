-- Tarea, otra vuelta de simplificacion: se retira lo que nadie usaba y el
-- responsable deja de capturarse a mano.
--
-- Se retiran `dependency` y `validation`
-- ---------------------------------------
-- El mismo defecto que ya tenian `leader`/`analyst` (retirados en
-- 20260922090000_simplificar_tarea_y_catalogo_de_fase.sql): enteros sueltos
-- sin llave foranea, que la pantalla ofrecia como si fueran una relacion real.
-- Ese archivo los dejo vivos "porque `dependency` y `validation` se quedan" --
-- pedido de negocio posterior (2026-09-24) es que tambien se vayan: la
-- pantalla de Tarea sobraba de campos que nadie llenaba con sentido.
--
-- Se retiran tambien `estimated_effort` y `task_code`
-- ----------------------------------------------------
-- Mismo pedido: texto libre sin validacion ni consumidor real (no aparecen en
-- ningun KPI, reporte o regla de negocio -- confirmado por busqueda en todo
-- `backend/app`). `task_code` en particular no se generaba solo, cada quien
-- capturaba lo que quisiera.
--
-- `owner` SI se queda -- sigue alimentando el KPI real "Desarrollo por
-- empleado" (`desarrollo_por_empleado_query`, `app/kpis/registry.py`) -- pero
-- deja de ser un campo de captura: `TaskService` ahora lo deriva SIEMPRE del
-- supervisor que tiene tomado el proyecto (`proyect.id_supervisor`), el mismo
-- que ya asigna `take_project`. Cambio de codigo, no de esquema; no hay nada
-- que migrar para eso.
--
-- Corre en cada arranque del pod: el DROP COLUMN usa IF EXISTS, como el resto
-- de esta cadena.

ALTER TABLE "task" DROP COLUMN IF EXISTS "dependency";
ALTER TABLE "task" DROP COLUMN IF EXISTS "validation";
ALTER TABLE "task" DROP COLUMN IF EXISTS "estimated_effort";
ALTER TABLE "task" DROP COLUMN IF EXISTS "task_code";
