-- "Nuevo" y "Usado" salen del estado del producto: la condicion de una pieza no
-- es dato que el almacen use, y como el selector no ofrecia "En almacen" (ENTRADA)
-- quien marcaba una pieza "usado" la sacaba de ahi para siempre -ni el formulario
-- ni el vale la devolvian-. El estado queda en: En almacen, En reparacion, Danado,
-- Retirado, Extraviado.
--
-- Lo que hoy esta en nuevo/usado pasa a "En almacen" (`product_status` = ENTRADA,
-- sin estado de catalogo, igual que lo escribe el formulario). Los dos estados se
-- desactivan del catalogo -no se borran: otras filas pueden apuntarles-, que es lo
-- que el selector respeta.
--
-- Se reaplica en cada arranque y es idempotente. Los dos estados quedan inactivos
-- siempre: reactivarlos a mano no sobrevive al siguiente arranque.

BEGIN;

DO $$
DECLARE
    afectados INTEGER;
BEGIN
    WITH viejos AS (
        SELECT id_inventory_status FROM inventory_status
         WHERE entity_scope = 'product' AND inventory_status_code IN ('nuevo', 'usado')
    ), cambiados AS (
        UPDATE product
           SET product_status = 'ENTRADA',
               id_inventory_status = NULL,
               last_update_date = CURRENT_TIMESTAMP
         WHERE lower(trim(coalesce(product_status, ''))) IN ('nuevo', 'usado')
            OR id_inventory_status IN (SELECT id_inventory_status FROM viejos)
        RETURNING 1
    )
    SELECT count(*) INTO afectados FROM cambiados;

    UPDATE inventory_status SET is_active = FALSE, last_update_date = CURRENT_TIMESTAMP
     WHERE entity_scope = 'product' AND inventory_status_code IN ('nuevo', 'usado')
       AND is_active;
    IF afectados > 0 THEN
        RAISE NOTICE 'Productos pasados de nuevo/usado a En almacen: %', afectados;
    END IF;
END $$;

COMMIT;
