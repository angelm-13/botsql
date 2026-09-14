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

-- 1. La entidad: tipos de material.
INSERT INTO entity_permission (
    id_permission, entity_name, control_type, menu_location,
    menu_group, menu_group_icon, menu_label, menu_order, created_by
)
SELECT p.id_permission, 'material_type', p.control_type, 'sidebar',
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
-- `LEAST(..., 3)` recorta a crear+leer. Un rol con CRUD completo sobre
-- productos recibe 3 y no 15: el vale no se borra ni se edita a mano, se cierra
-- por su renglon, y el bit de borrado abriria un camino para hacer desaparecer
-- el rastro.
INSERT INTO entity_permission (
    id_permission, entity_name, control_type, menu_location,
    menu_group, menu_group_icon, menu_label, menu_order, created_by
)
SELECT p.id_permission, 'warehouse_voucher',
       LEAST(p.control_type::integer, 3)::text, 'sidebar',
       'Inventario', 'inventory', 'Vales de almacen', 290, 1
FROM entity_permission p
WHERE p.entity_name = 'product'
  AND p.deletion_date IS NULL
  -- Quien solo consulta el almacen no levanta vales, pero si los lee: con
  -- control_type 2 el LEAST da 2, que es exactamente eso.
  AND p.control_type::integer > 0
  AND NOT EXISTS (
      SELECT 1 FROM entity_permission x
      WHERE x.id_permission = p.id_permission
        AND x.entity_name = 'warehouse_voucher'
  )
ON CONFLICT (id_permission, entity_name) DO NOTHING;

COMMIT;
