-- Roles de almacen, con separacion de funciones.
--
-- El problema que resuelve: quien opera el almacen y quien puede corregirlo
-- eran la misma persona. Bastaba el permiso de editar productos para hacer un
-- ajuste, que es el unico movimiento sin documento detras y sin tope: puede
-- crear existencia de la nada o destruirla por cualquier cantidad. Es la
-- operacion con la que se tapa un faltante.
--
-- Queda repartido asi:
--
--   Almacenista       recibe, despacha y traspasa. NO ajusta.
--   Jefe de almacen   todo lo anterior, y ademas ajusta y concilia.
--
-- El bit de control es una mascara: 1 crear, 2 leer, 4 actualizar, 8 borrar.
-- 7 = crear, leer y actualizar (sin borrar). 15 = todo.
--
-- Tambien se le da al Gerente el permiso sobre productos: ya tenia la
-- capacidad de ajustar, pero sin poder tocar productos no la podia ejercer, de
-- modo que la capacidad estaba concedida y era inservible.

BEGIN;

-- 1) Los dos roles, si no existen ya --------------------------------------
INSERT INTO permission (created_by, authorized_by, permission_description, id_department, id_subdepartment, id_level)
SELECT 1, 1, nombre.rol, 1, 1, 1
FROM (VALUES ('Almacenista'), ('Jefe de almacen')) AS nombre(rol)
WHERE NOT EXISTS (
    SELECT 1 FROM permission p
    WHERE lower(p.permission_description) = lower(nombre.rol)
      AND p.deletion_date IS NULL
);

-- 2) Sus capacidades -------------------------------------------------------
INSERT INTO entity_permission (id_permission, entity_name, control_type, menu_location, menu_group, menu_label, menu_order, created_by)
SELECT rol.id_permission, capacidad.entity_name, capacidad.control_type,
       capacidad.menu_location, capacidad.menu_group, capacidad.menu_label,
       capacidad.menu_order, 1
FROM permission rol
JOIN (VALUES
    -- Almacenista: opera el dia a dia.
    ('Almacenista', 'product',         7, 'sidebar', 'Inventario', 'Productos',            100),
    ('Almacenista', 'location',        6, 'sidebar', 'Inventario', 'Ubicaciones',          110),
    ('Almacenista', 'location_type',   2, 'none',    'Inventario', 'Tipo de ubicacion',    120),
    ('Almacenista', 'material',        6, 'sidebar', 'Inventario', 'Materiales',           130),
    ('Almacenista', 'unit',            2, 'none',    'Inventario', 'Unidades',             140),
    ('Almacenista', 'brand',           2, 'none',    'Inventario', 'Marcas',               150),
    ('Almacenista', 'inventory_status', 2, 'none',   'Inventario', 'Estado de inventario', 160),
    -- Jefe de almacen: ademas ajusta y corrige el catalogo.
    ('Jefe de almacen', 'product',              15, 'sidebar', 'Inventario', 'Productos',            100),
    ('Jefe de almacen', 'location',             15, 'sidebar', 'Inventario', 'Ubicaciones',          110),
    ('Jefe de almacen', 'location_type',        15, 'sidebar', 'Inventario', 'Tipo de ubicacion',    120),
    ('Jefe de almacen', 'material',             15, 'sidebar', 'Inventario', 'Materiales',           130),
    ('Jefe de almacen', 'unit',                 15, 'sidebar', 'Inventario', 'Unidades',             140),
    ('Jefe de almacen', 'brand',                15, 'sidebar', 'Inventario', 'Marcas',               150),
    ('Jefe de almacen', 'inventory_status',     15, 'sidebar', 'Inventario', 'Estado de inventario', 160),
    ('Jefe de almacen', 'inventory_adjustment',  2, 'none',    'Inventario', 'Ajustes',              170)
) AS capacidad(rol, entity_name, control_type, menu_location, menu_group, menu_label, menu_order)
  ON lower(rol.permission_description) = lower(capacidad.rol)
WHERE rol.deletion_date IS NULL
  AND NOT EXISTS (
    SELECT 1 FROM entity_permission ep
    WHERE ep.id_permission = rol.id_permission
      AND ep.entity_name = capacidad.entity_name
      AND ep.deletion_date IS NULL
  );

-- 3) El Gerente ya podia ajustar pero no tocar productos --------------------
INSERT INTO entity_permission (id_permission, entity_name, control_type, menu_location, menu_group, menu_label, menu_order, created_by)
SELECT p.id_permission, 'product', 15, 'sidebar', 'Inventario', 'Productos', 100, 1
FROM permission p
WHERE lower(p.permission_description) IN ('gerente', 'gerente_administrativo')
  AND p.deletion_date IS NULL
  AND NOT EXISTS (
    SELECT 1 FROM entity_permission ep
    WHERE ep.id_permission = p.id_permission
      AND ep.entity_name = 'product'
      AND ep.deletion_date IS NULL
  );

COMMIT;
