-- Que la busqueda del almacen no recorra la tabla entera.
--
-- Que se midio
-- ------------
-- La busqueda del rastreo usa `ILIKE '%texto%'` sobre `product.product_code`,
-- `product.descripcion` y `inventory_asset.asset_tag`. Un btree no sirve para
-- un patron que empieza por comodin, asi que Postgres recorre la tabla.
--
-- Con 5000 productos: recorrido completo, 1009 filas devueltas, 18 ms. No es el
-- cuello de botella hoy -lo era el numero de consultas, que ya se arreglo- pero
-- crece lineal: a 100 000 productos son del orden de 350 ms por tecleo, en una
-- pantalla que busca mientras se escribe.
--
-- Un indice de trigramas GIN si sirve para `%texto%`, y es la unica forma de
-- indexar esa clase de patron en Postgres.
--
-- Por que va dentro de un bloque con excepcion
-- --------------------------------------------
-- `CREATE EXTENSION pg_trgm` pide superusuario en Postgres 13 y posteriores. En
-- desarrollo el dueno de la base lo es; en un Postgres administrado -RDS, Cloud
-- SQL- puede no serlo, y entonces la sentencia falla.
--
-- Un fallo ahi no puede tumbar el despliegue: el initContainer aplica todas las
-- migraciones con ON_ERROR_STOP en cada arranque del pod, asi que una migracion
-- que revienta deja la base a medias y el backend arrancando contra un esquema
-- incompleto. Sin el indice la busqueda funciona igual, solo mas despacio, asi
-- que se avisa y se sigue.
--
-- Lo que NO se hace es CONCURRENTLY: no se puede dentro de una transaccion, y
-- estas migraciones corren en una. Con la tabla vacia o pequena -que es el caso
-- al aplicar- el bloqueo dura milisegundos. En una base ya grande, el indice se
-- crea a mano con CONCURRENTLY antes de desplegar y esta migracion lo encuentra
-- hecho y no hace nada.

BEGIN;

DO $$
BEGIN
    CREATE EXTENSION IF NOT EXISTS pg_trgm;

    CREATE INDEX IF NOT EXISTS ix_product_code_trgm
        ON product USING gin (product_code gin_trgm_ops);
    CREATE INDEX IF NOT EXISTS ix_product_descripcion_trgm
        ON product USING gin (descripcion gin_trgm_ops);
    CREATE INDEX IF NOT EXISTS ix_inventory_asset_tag_trgm
        ON inventory_asset USING gin (asset_tag gin_trgm_ops);

EXCEPTION WHEN insufficient_privilege OR feature_not_supported THEN
    -- Sin permiso para instalar la extension. La busqueda sigue funcionando con
    -- recorrido de tabla; se deja dicho en el log para que quien administre la
    -- base pueda crearla despues.
    RAISE WARNING 'pg_trgm no se pudo instalar (%). La busqueda del almacen '
                  'funcionara con recorrido de tabla. Para acelerarla: '
                  'CREATE EXTENSION pg_trgm; y los tres indices GIN de '
                  '20260903120000.', SQLERRM;
END $$;

COMMIT;
