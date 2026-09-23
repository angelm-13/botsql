-- Los permisos de las dos pantallas nuevas del almacen.
--
-- El registro ya las declara -`material_type` como entidad del modulo de
-- inventario y `warehouse_voucher` como capacidad- asi que una instalacion
-- nueva las siembra sola. Esta migracion es para las bases que ya existen: la
-- matriz de permisos no vuelve a pasar por ellas porque siembra con
-- `ON CONFLICT DO NOTHING`, y sin fila no hay nada que el gestor pueda editar
-- ni entrada que el menu pueda pintar.
--
-- El acceso se COPIA del que el rol ya tiene, no se escribe
-- ---------------------------------------------------------
-- `material_type` copia lo de `material`: el tipo es parte del material -su
-- tercer eje, junto a la familia y la marca- y quien captura materiales tiene
-- que poder capturar sus tipos. Escribir un valor fijo le daria alta de tipos a
-- quien solo consulta materiales, o se la negaria a quien los captura.
--
-- `warehouse_voucher` copia lo de `product`, acotado a crear y leer: levantar
-- un vale es capturar, y quien solo consulta el almacen solo consulta los
-- vales. No se le da el bit de borrar: un vale no se borra, se cierra, y su
-- rastro es la razon de llevarlo.
--
-- El gestor manda: si el par ya existe -vivo o retirado a proposito- no se
-- toca. Ver 20260903100000 para el mismo criterio.

BEGIN;

-- Guardado con un chequeo de existencia de scope_create: esta migracion es
-- anterior a 20260914110000_equipos_y_alcance_por_accion.sql, que agrega esas
-- 4 columnas y suelta control_type mas adelante en la misma pasada. Sin este
-- guardado, la primera pasada completa contra un volumen nuevo tronaria aqui
-- con "column scope_create does not exist".
DO $$
BEGIN
IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'entity_permission' AND column_name = 'scope_create'
) THEN

-- 1. La entidad: tipos de material.
INSERT INTO entity_permission (
    id_permission, entity_name, scope_create, scope_read, scope_update, scope_delete, menu_location,
    menu_group, menu_group_icon, menu_label, menu_order, created_by
)
SELECT p.id_permission, 'material_type',
       p.scope_create, p.scope_read, p.scope_update, p.scope_delete, 'sidebar',
       'Inventario', 'inventory', 'Tipos de material', 218, 1
FROM entity_permission p
WHERE p.entity_name = 'material'
  AND p.deletion_date IS NULL
  AND NOT EXISTS (
      SELECT 1 FROM entity_permission x
      WHERE x.id_permission = p.id_permission
        AND x.entity_name = 'material_type'
  )
ON CONFLICT (id_permission, entity_name) DO NOTHING;

-- 2. La capacidad: vales de almacen.
--
-- Se recorta a crear+leer (scope_update y scope_delete quedan en 0 sin
-- importar lo que tenga el rol sobre productos): el vale no se borra ni se
-- edita a mano, se cierra por su renglon, y el bit de borrado abriria un
-- camino para hacer desaparecer el rastro. Equivalente al viejo
-- `LEAST(control_type, 3)` (bits 1+2) ahora que el alcance vive en columnas
-- separadas.
INSERT INTO entity_permission (
    id_permission, entity_name, scope_create, scope_read, scope_update, scope_delete, menu_location,
    menu_group, menu_group_icon, menu_label, menu_order, created_by
)
SELECT p.id_permission, 'warehouse_voucher',
       p.scope_create, p.scope_read, 0, 0, 'sidebar',
       'Inventario', 'inventory', 'Vales de almacen', 290, 1
FROM entity_permission p
WHERE p.entity_name = 'product'
  AND p.deletion_date IS NULL
  -- Quien solo consulta el almacen no levanta vales, pero si los lee: con
  -- scope_read en "Todos" y scope_create en 0 esto da exactamente eso.
  AND (p.scope_create <> 0 OR p.scope_read <> 0 OR p.scope_update <> 0 OR p.scope_delete <> 0)
  AND NOT EXISTS (
      SELECT 1 FROM entity_permission x
      WHERE x.id_permission = p.id_permission
        AND x.entity_name = 'warehouse_voucher'
  )
ON CONFLICT (id_permission, entity_name) DO NOTHING;

END IF;
END $$;

COMMIT;
