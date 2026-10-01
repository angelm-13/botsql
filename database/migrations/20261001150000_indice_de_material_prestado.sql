-- Indice parcial para "Material prestado ahora" (KPI vivo `material_prestado_actual`).
--
-- Esa tabla ahora filtra, busca y cuenta en el servidor sobre TODOS los renglones prestados, no sobre
-- 50: cada apertura del tablero y cada tecla de la busqueda recorren los renglones de salida sin devolver.
-- Adser tiene 186 hoy, pero pueden ser miles, y los que importan son una fraccion pequena de
-- `nm_incident_product` (casi todo son renglones ya devueltos). Este indice cubre justo ese subconjunto,
-- con la MISMA condicion de la consulta (salida, sin borrar, sin devolver o con el centinela de Adser
-- `1990-01-01`), y entra por `id_incident` para el JOIN con `incident`.
--
-- `idx_nm_incident_product_abiertos` (due_date, solo `close_date IS NULL`) no sirve aqui: no cubre el
-- centinela, que es como Adser marca "sin devolver".
--
-- Idempotente (IF NOT EXISTS): estas migraciones corren completas en cada arranque.

CREATE INDEX IF NOT EXISTS idx_nm_incident_product_prestado
    ON nm_incident_product (id_incident)
    WHERE deletion_date IS NULL
      AND direction = 'salida'
      AND (close_date IS NULL OR close_date = TIMESTAMP '1990-01-01 00:00:00');
