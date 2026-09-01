-- Llaves foraneas diferibles, para que una base nueva se pueda sembrar.
--
-- El problema: `seed.sql` no podia aplicarse a una base limpia. Dos razones se
-- sumaban.
--
--   1. El orden de las sentencias no respeta las dependencias: 694 pares
--      quedan invertidos entre 56 tablas.
--   2. Peor aun, user, permission, proyect y customer_supplier se referencian
--      en circulo, y dos de esas columnas son obligatorias
--      (`permission.authorized_by` y `user.id_permission`). Ninguna puede
--      insertarse primero, asi que NINGUN orden de sentencias podria
--      funcionar: reordenar el archivo no era una salida.
--
-- La solucion es que la comprobacion se aplace al COMMIT durante la siembra.
-- Para eso las llaves tienen que ser diferibles.
--
-- `DEFERRABLE INITIALLY IMMEDIATE` no cambia el comportamiento normal: la
-- llave se sigue comprobando en cada sentencia, y los errores de la aplicacion
-- siguen saliendo donde ocurren. Lo unico que habilita es que una transaccion
-- pida explicitamente el aplazamiento, que es lo que ahora hace `seed.sql` con
-- `SET CONSTRAINTS ALL DEFERRED`.
--
-- No es un patron nuevo en este sistema: 122 de las llaves ya venian asi desde
-- `init.sql`. Esto alinea las 181 restantes.
--
-- Para una instalacion nueva no basta esta migracion, porque el arranque crea
-- el esquema desde los modelos: eso se resuelve en app/models/__init__.py.

BEGIN;

DO $$
DECLARE
    r record;
    ajustadas integer := 0;
BEGIN
    FOR r IN
        SELECT c.conname, c.conrelid::regclass AS tabla
        FROM pg_constraint c
        JOIN pg_namespace n ON n.oid = c.connamespace
        WHERE c.contype = 'f'
          AND NOT c.condeferrable
          AND n.nspname = 'public'
    LOOP
        EXECUTE format(
            'ALTER TABLE %%s ALTER CONSTRAINT %%I DEFERRABLE INITIALLY IMMEDIATE',
            r.tabla, r.conname
        );
        ajustadas := ajustadas + 1;
    END LOOP;
    RAISE NOTICE 'Llaves foraneas ajustadas: %%', ajustadas;
END $$;

COMMIT;
