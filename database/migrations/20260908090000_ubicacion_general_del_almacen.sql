-- La ubicacion general: donde vive lo que esta en el almacen sin sitio propio.
--
-- Que se reporto
-- --------------
-- Dos cosas que resultaron ser la misma:
--
--   1. "no salian los productos en localizar";
--   2. "el sistema original no define una ubicacion particular para muchas
--      cosas; hay que crear una ubicacion generica que abarque todo el almacen".
--
-- Medido con la base recien levantada
-- -----------------------------------
--     inventory_stock       0 filas
--     product.cantidad > 0  1 producto
--     location_type con is_warehouse = true   NINGUNO
--
-- Es decir: hay existencia -en `product.cantidad`- y no hay ni una fila de
-- existencia por ubicacion, ni un solo almacen declarado.
--
-- La pantalla de Localizar lee las ubicaciones de un producto SOLO de
-- `inventory_stock`. Sin fila ahi, el producto sale con `locations: []`: se ve,
-- pero no dice donde esta, y en cuanto alguien filtra por almacen desaparece.
-- El arbol de almacenes, por su parte, sale vacio porque ningun tipo de
-- ubicacion esta marcado como almacen.
--
-- Y la razon de fondo esta en el codigo:
--
--     if quantity <= 0 or not product.id_location:
--         return
--
-- `_ensure_stock_seeded` no siembra existencia de un producto SIN ubicacion. Y
-- solo corre dentro de un movimiento, asi que un producto recien dado de alta
-- no tiene fila hasta que alguien lo mueva. Lo que el sistema original entrega
-- sin ubicacion no entraba nunca.
--
-- Como queda
-- ----------
-- Una ubicacion marcada con `is_general_stock`. No es una ubicacion mas: es la
-- que contesta "esta en el almacen" cuando nadie dijo en que rack. Lo que se
-- localiza por unidad sigue teniendo su sitio; lo demas deja de ser invisible.
--
-- Solo puede haber una viva a la vez -indice unico parcial-, porque dos
-- "generales" partirian la existencia sin sitio entre dos montones y ninguno
-- seria el bueno.
--
-- Respeta lo que ya existe
-- ------------------------
-- Nada se sobreescribe:
--
--   * si ya hay un tipo de ubicacion marcado como almacen, se usa ese y no se
--     crea otro;
--   * si ya hay una ubicacion marcada como general, esta migracion no la toca;
--   * la existencia se siembra SOLO para productos que no tienen ninguna fila
--     en `inventory_stock`. Un producto con existencia ya repartida se queda
--     exactamente como esta;
--   * y se siembra en la ubicacion PROPIA del producto cuando la tiene; la
--     general es para los que no tienen ninguna.
--
-- Es el mismo criterio de siempre: el gestor manda.

BEGIN;

-- 1. La marca. Va en la ubicacion y no en una tabla aparte porque es una
--    propiedad de esa ubicacion, no una entidad nueva.
ALTER TABLE location
    ADD COLUMN IF NOT EXISTS is_general_stock BOOLEAN NOT NULL DEFAULT FALSE;

-- Dos ubicaciones generales partirian la existencia sin sitio en dos montones y
-- ninguno seria el bueno.
CREATE UNIQUE INDEX IF NOT EXISTS uq_location_general_stock
    ON location (is_general_stock)
    WHERE is_general_stock AND deletion_date IS NULL;

-- 2. Un tipo de ubicacion que sea almacen. Si ya hay uno, no se crea otro: el
--    arbol de almacenes se construye a partir de esta marca, y con dos tipos
--    "almacen" el mismo sitio aparece dos veces.
INSERT INTO location_type (location_type_description, is_warehouse, created_by)
SELECT 'Almacen', TRUE, 1
WHERE NOT EXISTS (
    SELECT 1 FROM location_type
    WHERE is_warehouse IS TRUE AND deletion_date IS NULL
);

-- 3. La ubicacion general, si nadie declaro una todavia.
INSERT INTO location (
    id_location_type, location_description, is_general_stock, created_by
)
SELECT
    (SELECT MIN(id_location_type) FROM location_type
      WHERE is_warehouse IS TRUE AND deletion_date IS NULL),
    'Almacen general',
    TRUE,
    1
WHERE NOT EXISTS (
    SELECT 1 FROM location
    WHERE is_general_stock IS TRUE AND deletion_date IS NULL
)
AND EXISTS (
    SELECT 1 FROM location_type
    WHERE is_warehouse IS TRUE AND deletion_date IS NULL
);

-- 4. La existencia que estaba solo en `product.cantidad` pasa a tener sitio.
--
--    Solo los productos SIN ninguna fila de existencia: uno que ya la tiene
--    repartida se queda como esta, aunque los numeros no coincidan. Cuadrar esa
--    diferencia es un conteo fisico, no una migracion que decide por su cuenta
--    cual de los dos numeros es el bueno.
INSERT INTO inventory_stock (id_product, id_location, quantity, created_by)
SELECT
    p.id_product,
    -- Su propia ubicacion cuando la tiene y sigue viva; la general cuando no.
    COALESCE(
        (SELECT l.id_location FROM location l
          WHERE l.id_location = p.id_location AND l.deletion_date IS NULL),
        (SELECT g.id_location FROM location g
          WHERE g.is_general_stock IS TRUE AND g.deletion_date IS NULL)
    ),
    p.cantidad,
    COALESCE(p.created_by, 1)
FROM product p
WHERE p.deletion_date IS NULL
  AND COALESCE(p.cantidad, 0) > 0
  AND NOT EXISTS (
      SELECT 1 FROM inventory_stock s WHERE s.id_product = p.id_product
  )
  AND EXISTS (
      SELECT 1 FROM location g
      WHERE g.is_general_stock IS TRUE AND g.deletion_date IS NULL
  );

COMMIT;
