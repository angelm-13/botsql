-- La fila que faltaba en el catalogo de estatus, y los 65 productos que la
-- estaban esperando.
--
-- Que paso
-- --------
-- `importar_sistema_anterior.py` traduce el `producto.estado` del sistema
-- anterior al catalogo con este mapa:
--
--     DESTRUCCION  -> retirado
--     EXTRAVIADO   -> extraviado
--     DANADO       -> danado
--
-- y 20260904090000 siembra el catalogo con CINCO codigos: nuevo, usado,
-- en_reparacion, danado y retirado. `extraviado` no esta.
--
-- El importador resuelve el codigo con `catalogo_estado.get(codigo)`, que
-- devuelve None cuando no existe, y sigue adelante. Resultado medido en la base
-- de desarrollo, con los datos reales dentro:
--
--     product_status  | sin fila de catalogo | total
--     ----------------+----------------------+-------
--     DESTRUCCION     |                    0 |    86
--     DANADO          |                    0 |    27
--     EQ. DANADOS     |                    0 |    11
--     EXTRAVIADO      |                   65 |    65   <-- todos
--
-- Los 65 conservan la cadena original en `product_status` -- de ahi los pinta
-- Localizar, y por eso el fallo no se veia en pantalla --, pero cualquier
-- consulta que agrupe por el catalogo los cuenta de menos. Que es justo lo que
-- el catalogo existe para hacer.
--
-- ENTRADA y SALIDA se quedan sin fila a proposito: son direccion de movimiento,
-- no estado de la pieza, y el mapa no los traduce.
--
-- Por que una migracion nueva y no arreglar la de 20260904090000
-- --------------------------------------------------------------
-- Editar aquella funcionaria -- `db-migrate` reaplica todas en cada arranque y
-- su INSERT esta guardado por NOT EXISTS --, pero deja la historia mintiendo:
-- diria que el catalogo siempre tuvo seis codigos y que nunca hubo 65 filas mal
-- cargadas. Esto se descubrio hoy, contando, y asi queda escrito.

BEGIN;

-- 1. El codigo que faltaba.
--
-- El departamento y el nivel se RESUELVEN de lo que exista, igual que en
-- 20260904090000: las dos columnas son NOT NULL con un DEFAULT que apunta a
-- identificadores que no existen en toda base, y ahi el INSERT revienta contra
-- la llave ajena en el COMMIT.
--
-- Rojo, y no terminal: extraviado no es fin de vida como `retirado` -- una
-- pieza perdida puede aparecer, y de hecho es la razon de tener el estado en
-- lugar de darla de baja --. El orden lo pone entre danado (40) y retirado (50).
INSERT INTO inventory_status (
    inventory_status_code, inventory_status_description, color,
    entity_scope, is_active, is_terminal, sort_order,
    id_department, id_subdepartment, id_minimum_level, created_by
)
SELECT 'extraviado', 'Extraviado', '#dc2626', 'product', TRUE, FALSE, 45,
       (SELECT MIN(id_department) FROM department WHERE deletion_date IS NULL),
       NULL,
       (SELECT MIN(id_level) FROM level WHERE deletion_date IS NULL),
       1
WHERE EXISTS (SELECT 1 FROM department WHERE deletion_date IS NULL)
  AND EXISTS (SELECT 1 FROM level WHERE deletion_date IS NULL)
  AND NOT EXISTS (
    SELECT 1 FROM inventory_status s
    WHERE s.inventory_status_code = 'extraviado'
      AND s.entity_scope = 'product'
  );

-- 2. Los productos que la esperaban.
--
-- Solo los que tienen la cadena y NO tienen fila: un producto al que alguien le
-- puso otro estatus a mano ya dijo lo que queria, y esto no lo pisa. Por eso el
-- `id_inventory_status IS NULL` no es una optimizacion, es la regla.
--
-- La comparacion normaliza la enye porque en estos datos conviven las dos
-- formas -- "DANADO" y "DAÑADO" --, y aunque EXTRAVIADO no la lleve, la misma
-- expresion sirve si mañana se añade otro codigo.
UPDATE product p
   SET id_inventory_status = (
           SELECT s.id_inventory_status FROM inventory_status s
           WHERE s.inventory_status_code = 'extraviado'
             AND s.entity_scope = 'product'
             AND s.deletion_date IS NULL
           LIMIT 1
       ),
       last_update_date = now()
 WHERE p.deletion_date IS NULL
   AND p.id_inventory_status IS NULL
   AND upper(translate(trim(p.product_status), 'Ñ', 'N')) = 'EXTRAVIADO'
   AND EXISTS (
       SELECT 1 FROM inventory_status s
       WHERE s.inventory_status_code = 'extraviado'
         AND s.entity_scope = 'product'
         AND s.deletion_date IS NULL
   );

COMMIT;
