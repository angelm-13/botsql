-- El asiento de apertura de lo que trajo la carga del sistema anterior.
--
-- Que estaba mal
-- --------------
-- `importar_sistema_anterior.py` siembra `inventory_stock` y `product.cantidad`
-- directamente, sin escribir el libro. Resultado medido:
--
--     productos importados ................. 2 220
--     con algun asiento en el libro .........   224   (los que salieron en vale)
--     con existencia > 0 y el libro vacio ... 1 977
--
-- El libro dice que nunca entro nada y la existencia dice que hay 2 209
-- unidades. La propia pantalla lo detecta y lo canta en cada ficha:
--
--     "Descuadre detectado entre el libro y la existencia.
--      libro: 0 · existencia: 1 · movimientos: 0"
--
-- Y no es un aviso decorativo: el libro es lo que contesta "como llego la
-- existencia al numero de hoy". Vacio, esa pregunta no tiene respuesta para el
-- 89% del almacen, y cualquier auditoria empieza y termina ahi.
--
-- Que hace esto
-- -------------
-- Escribe UN asiento de apertura por producto, con la cantidad que hacia falta
-- para que el libro explique el saldo:
--
--     apertura = cantidad de hoy - suma de los asientos que ya existen
--
-- Para los 1 977 sin asientos eso es su cantidad tal cual. Para los 224 que ya
-- salieron en un vale es 1: hoy tienen 0 y el libro tiene un -1, asi que la
-- apertura de 1 deja la cadena cuadrada -- entra 1, sale 1, queda 0 -- en vez
-- de un libro que empieza restando.
--
-- Se AÑADE, no se corrige nada. El libro es de solo agregado por diseño y esta
-- migracion no toca `product.cantidad`, ni `inventory_stock`, ni ningun asiento
-- existente: la existencia de hoy es la buena y es la que manda; lo que faltaba
-- era el renglon que la explica.
--
-- La fecha es la de creacion del producto, y nunca posterior al primer asiento
-- que ya tenga: una apertura fechada despues de la salida que la consume seria
-- un libro que se lee al reves.
--
-- Idempotente por `idempotency_key`: `db-migrate` reaplica todas las
-- migraciones en cada arranque, y la tabla no tiene indice unico sobre esa
-- columna, asi que la guarda es el NOT EXISTS de abajo.

BEGIN;

INSERT INTO inventory_ledger (
    id_product, id_proyect, movement_type, source_module,
    quantity_delta, balance_after, id_location, location_balance_after,
    idempotency_key, reference_type, reference_id, reason,
    created_by, creation_date
)
SELECT
    p.id_product,
    -- El mismo proyecto con el que la carga escribio los 224 asientos que si
    -- existen: separarlos en otro haria que las dos mitades del libro de un
    -- mismo producto colgaran de proyectos distintos.
    1,
    'opening',
    'nucleo',
    p.cantidad - COALESCE(l.suma, 0),
    p.cantidad - COALESCE(l.suma, 0),
    p.id_location,
    -- El saldo POR UBICACION se deja en nulo a proposito: solo se puede afirmar
    -- cuando el producto tiene una sola, y afirmarlo cuando tiene varias seria
    -- inventar en que estante estaba cada pieza el dia de la carga.
    NULL,
    'import:adser_prod:apertura:' || p.external_id,
    'migration',
    p.external_id,
    'Existencia inicial de la carga del sistema anterior',
    1,
    LEAST(
        COALESCE(p.creation_date, now()),
        COALESCE(l.primero, COALESCE(p.creation_date, now()))
    )
FROM product p
LEFT JOIN (
    SELECT id_product, sum(quantity_delta) AS suma, min(creation_date) AS primero
    FROM inventory_ledger
    GROUP BY id_product
) l ON l.id_product = p.id_product
WHERE p.external_source IS NOT NULL
  AND p.external_id IS NOT NULL
  AND p.deletion_date IS NULL
  -- Un producto que hoy esta en cero y nunca se movio no necesita apertura: su
  -- libro vacio ya explica su saldo vacio.
  AND p.cantidad - COALESCE(l.suma, 0) <> 0
  AND NOT EXISTS (
      SELECT 1 FROM inventory_ledger x
      WHERE x.idempotency_key = 'import:adser_prod:apertura:' || p.external_id
  );

COMMIT;
