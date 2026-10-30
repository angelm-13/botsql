-- Foto del material.
--
-- Pedido de almacen: el material ("Desarmador Truper punta plana") es lo que se
-- reconoce a simple vista, no cada pieza concreta, asi que su foto se captura
-- una vez en Materiales y la heredan todos los productos que no traen la suya
-- (Almacen, Localizar, Productos, Vales).
--
-- Mismo formato de ruta que `product.path_imagen` (`uploads/products/m_<id>.<ext>`;
-- vive en la carpeta de productos para que la sirva la misma ruta y el mismo
-- volumen persistente, y el prefijo `m_` no choca con el `p_` de las fotos de
-- producto).
--
-- Se reaplica en cada arranque del pod (sin tabla de control): ADD COLUMN IF NOT
-- EXISTS no hace nada la segunda vez.
BEGIN;

ALTER TABLE material
    ADD COLUMN IF NOT EXISTS path_imagen VARCHAR(100);

COMMIT;
