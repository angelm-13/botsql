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
-- ON CONFLICT en vez de NOT EXISTS (deletion_date IS NULL): mismo motivo que
-- 20260828140000 -- 20260828240000 da de baja logica toda la tabla y la
-- resiembra desde el registro de modulos, y estas entidades pueden quedar
-- fuera de esa resiembra para alguno de estos roles. Un reinicio del pod
-- reaplica las 45 migraciones desde cero, y un NOT EXISTS que solo mira filas
-- activas choca contra la fila fantasma que dejo la resiembra anterior.
--
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

INSERT INTO entity_permission (id_permission, entity_name, scope_create, scope_read, scope_update, scope_delete, menu_location, menu_group, menu_label, menu_order, created_by)
SELECT rol.id_permission, capacidad.entity_name,
       capacidad.scope_create, capacidad.scope_read, capacidad.scope_update, capacidad.scope_delete,
       capacidad.menu_location, capacidad.menu_group, capacidad.menu_label,
       capacidad.menu_order, 1
FROM permission rol
JOIN (VALUES
    -- Almacenista: opera el dia a dia.
    -- control_type original -> scope_create/scope_read/scope_update/scope_delete
    -- (bit ON = 4 "Todos", bit OFF = 0, misma conversion que
    -- 20260914110000_equipos_y_alcance_por_accion.sql)
    ('Almacenista', 'product',         4, 4, 4, 0, 'sidebar', 'Inventario', 'Productos',            100),
    ('Almacenista', 'location',        0, 4, 4, 0, 'sidebar', 'Inventario', 'Ubicaciones',          110),
    ('Almacenista', 'location_type',   0, 4, 0, 0, 'hidden',    'Inventario', 'Tipo de ubicacion',    120),
    ('Almacenista', 'material',        0, 4, 4, 0, 'sidebar', 'Inventario', 'Materiales',           130),
    ('Almacenista', 'unit',            0, 4, 0, 0, 'hidden',    'Inventario', 'Unidades',             140),
    ('Almacenista', 'brand',           0, 4, 0, 0, 'hidden',    'Inventario', 'Marcas',               150),
    ('Almacenista', 'inventory_status', 0, 4, 0, 0, 'hidden',   'Inventario', 'Estado de inventario', 160),
    -- Jefe de almacen: ademas ajusta y corrige el catalogo.
    ('Jefe de almacen', 'product',              4, 4, 4, 4, 'sidebar', 'Inventario', 'Productos',            100),
    ('Jefe de almacen', 'location',             4, 4, 4, 4, 'sidebar', 'Inventario', 'Ubicaciones',          110),
    ('Jefe de almacen', 'location_type',        4, 4, 4, 4, 'sidebar', 'Inventario', 'Tipo de ubicacion',    120),
    ('Jefe de almacen', 'material',             4, 4, 4, 4, 'sidebar', 'Inventario', 'Materiales',           130),
    ('Jefe de almacen', 'unit',                 4, 4, 4, 4, 'sidebar', 'Inventario', 'Unidades',             140),
    ('Jefe de almacen', 'brand',                4, 4, 4, 4, 'sidebar', 'Inventario', 'Marcas',               150),
    ('Jefe de almacen', 'inventory_status',     4, 4, 4, 4, 'sidebar', 'Inventario', 'Estado de inventario', 160),
    ('Jefe de almacen', 'inventory_adjustment',  0, 4, 0, 0, 'hidden',    'Inventario', 'Ajustes',              170)
) AS capacidad(rol, entity_name, scope_create, scope_read, scope_update, scope_delete, menu_location, menu_group, menu_label, menu_order)
  ON lower(rol.permission_description) = lower(capacidad.rol)
WHERE rol.deletion_date IS NULL
ON CONFLICT (id_permission, entity_name) DO NOTHING;

-- 3) El Gerente ya podia ajustar pero no tocar productos --------------------
INSERT INTO entity_permission (id_permission, entity_name, scope_create, scope_read, scope_update, scope_delete, menu_location, menu_group, menu_label, menu_order, created_by)
SELECT p.id_permission, 'product', 4, 4, 4, 4, 'sidebar', 'Inventario', 'Productos', 100, 1
FROM permission p
WHERE lower(p.permission_description) IN ('gerente', 'gerente_administrativo')
  AND p.deletion_date IS NULL
ON CONFLICT (id_permission, entity_name) DO NOTHING;

END IF;
END $$;

COMMIT;
