-- Enlace entre un producto del nucleo y el del punto de venta.
--
-- El POS corre contra su propia base, asi que sus productos no pueden ser filas
-- de `product`: son otro sistema. Sin un enlace, "un solo inventario" se queda
-- en la intencion, porque una venta del POS no tiene forma de decir que
-- producto del nucleo descontar.
--
-- El enlace es explicito y no por nombre. Emparejar por descripcion parece
-- comodo hasta que dos productos se llaman casi igual y las ventas empiezan a
-- descontar del renglon equivocado, sin que nada avise.
--
-- Un producto del POS sin enlace simplemente no descuenta, y se reporta. Es
-- preferible a inventar una correspondencia: un inventario que descuenta del
-- producto equivocado es peor que uno que no descuenta.

BEGIN;

CREATE TABLE IF NOT EXISTS pos_product_link (
    id_pos_product_link serial PRIMARY KEY,
    id_product          integer NOT NULL REFERENCES product (id_product),
    -- El identificador del producto en la base del POS. Es un UUID de otro
    -- sistema, asi que se guarda como texto y no como referencia.
    pos_product_id      varchar(64) NOT NULL,
    pos_product_name    varchar(200),
    -- Ubicacion del nucleo donde se descuenta lo que el POS vende.
    id_location         integer NOT NULL REFERENCES location (id_location),

    created_by          integer NOT NULL,
    creation_date       timestamp NOT NULL DEFAULT now(),
    last_update_date    timestamp NOT NULL DEFAULT now(),
    deletion_date       timestamp,

    -- Un producto del POS descuenta de un solo producto del nucleo: dos
    -- enlaces dejarian la venta descontando dos veces.
    CONSTRAINT uq_pos_product_link UNIQUE (pos_product_id)
);

CREATE INDEX IF NOT EXISTS idx_pos_product_link_product ON pos_product_link (id_product);

COMMIT;
