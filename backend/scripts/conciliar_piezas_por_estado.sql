-- SOLO LECTURA. Categoria de cada pieza segun la regla de `piezas_por_estado`
-- (backend/app/kpis/registry.py, `piezas_por_estado_query`):
--   Destruccion > Extraviado > Dañado > En reparación > Salida > Entrada
-- Una fila por pieza (`product` sin borrar): "id_producto,categoria".
--
--   psql -At -F, -f conciliar_piezas_por_estado.sql > piezas.csv
--   python3 backend/scripts/conciliar_piezas_por_estado.py piezas.csv \
--       docs/despliegues/2026-09-30_estado_de_piezas_adser.csv
--
-- Si cambia la regla del KPI, cambia aqui tambien.
BEGIN READ ONLY;
WITH abiertas AS (
  SELECT DISTINCT nip.id_product
    FROM nm_incident_product nip
    JOIN incident i ON i.id_incident = nip.id_incident AND i.deletion_date IS NULL
    LEFT JOIN incident_type t ON t.id_incident_type = i.id_incident_type
   WHERE nip.deletion_date IS NULL
     AND i.incident_date IS NOT NULL
     AND nip.direction = 'salida'
     AND (nip.close_date IS NULL OR nip.close_date = TIMESTAMP '1990-01-01')
     AND (t.incident_type_description IS NULL
          OR lower(trim(t.incident_type_description)) NOT IN ('destruccion', 'destrucción', 'extraviado'))
)
SELECT p.id_product,
       CASE
         WHEN lower(trim(s.inventory_status_code)) = 'retirado'      THEN 'Destruccion'
         WHEN lower(trim(s.inventory_status_code)) = 'extraviado'    THEN 'Extraviado'
         WHEN lower(trim(s.inventory_status_code)) = 'danado'        THEN 'Dañado'
         WHEN lower(trim(s.inventory_status_code)) = 'en_reparacion' THEN 'En reparación'
         WHEN a.id_product IS NOT NULL                               THEN 'Salida'
         ELSE 'Entrada'
       END AS categoria
  FROM product p
  LEFT JOIN inventory_status s ON s.id_inventory_status = p.id_inventory_status
  LEFT JOIN abiertas a ON a.id_product = p.id_product
 WHERE p.deletion_date IS NULL
 ORDER BY p.id_product;
ROLLBACK;
