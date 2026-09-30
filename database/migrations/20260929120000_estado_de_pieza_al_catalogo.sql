-- Los estados de pieza que `migrate_adser.py` dejo solo en texto.
--
-- El sistema anterior guardaba en `producto.estado` DOS cosas mezcladas:
-- direccion de movimiento (ENTRADA, SALIDA) y estado de la pieza (DESTRUCCION,
-- DAÑADO, EQ. DAÑADOS, EXTRAVIADO). Solo las segundas son estados; el catalogo
-- `inventory_status` (alcance `product`) existe para ellas y las consultas que
-- agrupan por estado leen de ahi, no del texto libre `product_status`.
--
-- `importar_sistema_anterior.py` ya traduce con este mapa:
--
--     DESTRUCCION  -> retirado
--     DAÑADO / EQ. DAÑADOS -> danado
--     EXTRAVIADO   -> extraviado   (aplicado por 20260909100000)
--
-- pero `migrate_adser.py` no lo hizo: en adser (medido 2026-09-29 en
-- tyakxa-dev y adser-prod) los 65 EXTRAVIADO ya estan en el catalogo por la
-- migracion de septiembre 9, y los otros 124 -- 86 DESTRUCCION, 27 DAÑADO y 11
-- EQ. DAÑADOS -- tienen `id_inventory_status` NULL, asi que cualquier reporte
-- por estado los cuenta de menos.
--
-- Mismo patron que 20260909100000, y por las mismas razones:
--   * solo toca productos SIN estado de catalogo: uno al que alguien le puso otro
--     estado a mano ya dijo lo que queria, y esto no lo pisa;
--   * no toca `product_status`: la cadena original se conserva, es de donde
--     pintan las pantallas viejas;
--   * ENTRADA y SALIDA se quedan sin fila a proposito: son direccion, no estado;
--   * si el catalogo no tiene el codigo, no hace nada (replay seguro: estas
--     migraciones corren completas en cada arranque del backend).
--
-- Instalaciones sin esos textos (torredigital, vidrioyaluminios): no toca nada.

UPDATE product p
   SET id_inventory_status = s.id_inventory_status,
       last_update_date = now()
  FROM inventory_status s
 WHERE s.entity_scope = 'product'
   AND s.deletion_date IS NULL
   AND p.deletion_date IS NULL
   AND p.id_inventory_status IS NULL
   AND (
        (s.inventory_status_code = 'retirado'
         AND upper(translate(trim(p.product_status), 'Ñ', 'N')) = 'DESTRUCCION')
     OR (s.inventory_status_code = 'danado'
         AND upper(translate(trim(p.product_status), 'Ñ', 'N')) IN ('DANADO', 'EQ. DANADOS'))
   );
