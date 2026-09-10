-- El enlace que le faltaba a restaurante y logistica para compartir inventario.
--
-- La decision ya estaba tomada y escrita
-- --------------------------------------
-- `app/services/pos_inventory_bridge.py` lo dice en su cabecera: "la decision es
-- que haya un solo inventario para todos los proyectos". Y el propio libro lo
-- contempla desde 20260901140000:
--
--     CHECK (source_module IN ('nucleo', 'pos', 'restaurante', 'logistica'))
--
-- El punto de venta ya lo cumple: cuando cobra una venta escribe el movimiento
-- en `inventory_ledger` con `source_module = 'pos'`. Restaurante y logistica no,
-- porque les faltaba lo mismo que el POS si tiene: saber QUE producto del nucleo
-- corresponde a cada insumo suyo.
--
-- Por que una columna y no una tabla puente
-- -----------------------------------------
-- El POS usa `pos_product_link` porque corre contra OTRA base: su producto es un
-- identificador ajeno, y hace falta una tabla que empareje dos mundos.
--
-- Restaurante y logistica viven en esta misma base, asi que su insumo puede
-- apuntar al producto directamente. Una tabla puente aqui seria una indireccion
-- sin nada que resolver, y una fila mas que mantener sincronizada.
--
-- Nulo a proposito
-- ----------------
-- Un insumo sin enlace sigue funcionando como hasta hoy: lleva su saldo propio y
-- no toca el nucleo. Es lo que permite adoptar esto insumo por insumo en lugar
-- de exigir que alguien empareje el catalogo entero antes de poder vender un
-- platillo.
--
-- Y NO se adivina la correspondencia por nombre. El POS ya explica por que:
-- emparejar por nombre parece comodo hasta que dos se llaman casi igual y el
-- consumo descuenta del renglon equivocado sin que nada avise. Un inventario que
-- descuenta del producto equivocado es peor que uno que no descuenta, porque el
-- primero se ve sano.

BEGIN;

-- El insumo del restaurante -- harina, aceite -- y el producto del almacen que
-- lo representa.
ALTER TABLE restaurant_inventory_item
    ADD COLUMN IF NOT EXISTS id_product INTEGER
        REFERENCES product(id_product) DEFERRABLE INITIALLY IMMEDIATE;

CREATE INDEX IF NOT EXISTS idx_restaurant_inventory_item_product
    ON restaurant_inventory_item (id_product);

-- Lo mismo para la mercancia que logistica guarda por cuenta de un cliente.
ALTER TABLE logistics_inventory
    ADD COLUMN IF NOT EXISTS id_product INTEGER
        REFERENCES product(id_product) DEFERRABLE INITIALLY IMMEDIATE;

CREATE INDEX IF NOT EXISTS idx_logistics_inventory_product
    ON logistics_inventory (id_product);

-- Y la ubicacion del nucleo contra la que se mueve. Sin ella habria que elegir
-- una por omision, y "la primera nave que aparezca" es exactamente el tipo de
-- suposicion que deja existencia en el sitio equivocado.
ALTER TABLE restaurant_inventory_item
    ADD COLUMN IF NOT EXISTS id_location INTEGER
        REFERENCES location(id_location) DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE logistics_inventory
    ADD COLUMN IF NOT EXISTS id_core_location INTEGER
        REFERENCES location(id_location) DEFERRABLE INITIALLY IMMEDIATE;

COMMIT;
