-- Un solo inventario para todos los proyectos.
--
-- El cambio de criterio
-- ---------------------
-- Hasta ahora cada modulo llevaba su propio almacen en tablas separadas, y eso
-- estaba declarado y probado. La decision ahora es la contraria: un solo
-- inventario que registre las entradas y salidas de todos los proyectos -punto
-- de venta, restaurante, logistica y el nucleo- sin que queden entidades
-- sueltas.
--
-- Juntos pero distinguibles
-- -------------------------
-- «Un solo inventario» no significa perder de vista de donde viene cada
-- movimiento. `inventory_ledger.source_module` dice que proyecto lo provoco, de
-- modo que la existencia es una sola y el origen sigue siendo legible. Separar
-- por tabla obligaba a preguntar en tres sitios para saber cuanto hay; separar
-- por columna deja las dos preguntas contestables.
--
-- Se eligio columna y no tabla por lo que ya paso: con tres cadenas de tablas,
-- una consulta que olvidaba una devolvia un saldo incompleto sin avisar.
--
-- Que se agrega
-- -------------
-- 1. `source_module` en el libro y en la existencia por ubicacion.
-- 2. El tipo de movimiento que faltaba: caducidad. Estaban entrada, devolucion,
--    salida, prestamo, merma, dano, destruccion y ajuste, pero lo que se vence
--    se registraba como merma, y no es lo mismo: la merma se puede reducir
--    operando mejor y la caducidad se reduce comprando mejor.
-- 3. `id_module` en la ubicacion, para que el almacen de cada proyecto sea una
--    rama del mismo arbol en lugar de un almacen aparte.

BEGIN;

-- --- de donde viene cada movimiento -------------------------------------

ALTER TABLE inventory_ledger
    ADD COLUMN IF NOT EXISTS source_module varchar(20) NOT NULL DEFAULT 'nucleo';

ALTER TABLE inventory_ledger DROP CONSTRAINT IF EXISTS ck_inventory_ledger_source_module;
ALTER TABLE inventory_ledger
    ADD CONSTRAINT ck_inventory_ledger_source_module
    CHECK (source_module IN ('nucleo', 'pos', 'restaurante', 'logistica'));

COMMENT ON COLUMN inventory_ledger.source_module IS
    'Proyecto que provoco el movimiento. La existencia es una sola; esto dice de donde viene.';

-- La consulta natural del responsable de almacen: que movio cada proyecto.
CREATE INDEX IF NOT EXISTS idx_inventory_ledger_source_module
    ON inventory_ledger (source_module, id_inventory_ledger DESC);


-- --- la ubicacion sabe de que proyecto es --------------------------------
--
-- El almacen de cada proyecto es una rama del mismo arbol de ubicaciones, no un
-- almacen aparte. Asi «cuanto hay en total» y «cuanto hay del restaurante» se
-- contestan con la misma consulta y un filtro.

ALTER TABLE location
    ADD COLUMN IF NOT EXISTS id_module varchar(20);

ALTER TABLE location DROP CONSTRAINT IF EXISTS ck_location_module;
ALTER TABLE location
    ADD CONSTRAINT ck_location_module
    CHECK (id_module IS NULL OR id_module IN ('nucleo', 'pos', 'restaurante', 'logistica'));

COMMENT ON COLUMN location.id_module IS
    'Proyecto al que pertenece esta ubicacion. Nulo = comun a todos.';

CREATE INDEX IF NOT EXISTS idx_location_module ON location (id_module);


-- --- las tablas de almacen que quedan sin uso ----------------------------
--
-- `logistics_inventory`, `logistics_warehouse` y `logistics_location` estan
-- vacias -cero filas al momento de esta migracion-, asi que no hay dato que
-- migrar: lo que habia era la estructura, no el contenido.
--
-- NO se borran aqui. Sus rutas y modelos siguen en el codigo, y quitar la tabla
-- antes que el codigo deja el sistema reventando en la primera consulta. Se
-- marcan para que nadie las adopte creyendo que son el camino, y se retiran
-- cuando su codigo se haya redirigido al inventario unico.

COMMENT ON TABLE logistics_inventory IS
    'EN RETIRO: el inventario unico vive en inventory_stock / inventory_ledger. '
    'No agregar filas aqui; esta tabla se elimina cuando su codigo se redirija.';
COMMENT ON TABLE logistics_warehouse IS
    'EN RETIRO: un almacen es una location con location_type.is_warehouse.';
COMMENT ON TABLE restaurant_inventory_item IS
    'EN RETIRO: los insumos del restaurante pasan a product con su ubicacion '
    'propia dentro del arbol comun.';

COMMIT;
