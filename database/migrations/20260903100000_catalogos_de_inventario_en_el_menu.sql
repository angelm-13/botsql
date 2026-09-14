-- Lo que el registro nombra y la base dejo escondido.
--
-- Que estaba mal
-- --------------
-- Preguntando "y para anadir nuevos productos o familias de productos como le
-- hago?" salio que no habia forma de hacerlo desde el menu.
--
-- Medido en la base: `product_family` existia para tres roles -Administrator,
-- Supervisor y Gerente-, los tres con `menu_location = 'hidden'` y sin
-- etiqueta, y no existia en absoluto para Almacenista ni para Jefe de almacen,
-- que son los dos que trabajan el almacen. Es decir: nadie podia dar de alta
-- una familia de producto.
--
-- Revisando salio que no era solo eso. El rol Administrator tenia 29 filas
-- escondidas y sin etiqueta, y de esas 7 son entidades que el registro SI
-- nombra: Productos, Materiales, Ubicaciones, Tipos de ubicacion, Tareas, Notas
-- de tarea y Tipos de tarea. El permiso estaba concedido, la pantalla existia y
-- su ruta tambien, pero no habia entrada de menu. Una funcionalidad a la que
-- solo se llega escribiendo la direccion a mano es una funcionalidad que no
-- existe.
--
-- Por que estaba escondido
-- ------------------------
-- Dos causas distintas.
--
-- La primera: el registro de modulos decide la ubicacion asi:
--
--     "sidebar" if etiqueta else "hidden"
--
-- y `product_family`, `brand`, `unit` e `inventory_status` no tenian entrada en
-- el mapa MENU. No fue una decision de ocultarlos: fue no haberlos nombrado. El
-- registro ya se corrigio; esta migracion arregla las bases que ya existen.
--
-- La segunda: las filas de Administrator, Supervisor y Gerente sobre `product`,
-- `material`, `location`, `task`... vienen de antes de que existiera la
-- navegacion por rol, asi que nacieron sin etiqueta y en `hidden`, y ninguna
-- migracion posterior las nombro porque ninguna pisa filas existentes.
--
-- Que toca y que no
-- -----------------
-- El gestor manda, asi que solo se nombran las filas que NADIE nombro:
-- `menu_label IS NULL`. Una fila con etiqueta la puso una persona -o una
-- migracion anterior- eligiendo donde va, y pisarla revertiria su trabajo.
-- Medido al aplicarla: la fila de `brand` del Almacenista dice `hidden` con
-- etiqueta "Marcas", y se queda como esta.
--
-- Tampoco se toca `control_type`: quien solo consulta el inventario sigue solo
-- consultando. Ver la familia en el menu no da permiso de crearla; para eso
-- esta el gestor, que ya ofrece las cuatro entidades.
--
-- La lista de abajo se genero desde `filas_de_permisos()`, no a mano:
-- transcribir treinta y siete etiquetas es donde se cuela la que queda mal
-- escrita y nadie revisa.

BEGIN;

-- 1. Nombrar y sacar del escondite lo que el registro nombra y nadie nombro.
UPDATE entity_permission ep
SET menu_location = 'sidebar',
    menu_group = c.grupo,
    menu_group_icon = c.icono,
    menu_label = c.etiqueta,
    menu_order = c.orden,
    last_update_date = now()
FROM (VALUES
    ('bank', 'Bancos', 'Facturacion', 'billing', 140),
    ('bank_account', 'Cuentas bancarias', 'Facturacion', 'billing', 150),
    ('brand', 'Marcas', 'Inventario', 'inventory', 214),
    ('customer_supplier', 'Clientes y proveedores', 'CRM', 'crm', 620),
    ('department', 'Departamentos', 'Configuracion', 'settings', 830),
    ('fiscal_account', 'Cuentas fiscales', 'Facturacion', 'billing', 130),
    ('incident', 'Incidencias', 'Operaciones', 'operations', 350),
    ('incident_detail', 'Detalle de incidencias', 'Operaciones', 'operations', 360),
    ('inventory_status', 'Estado de inventario', 'Inventario', 'inventory', 270),
    ('invoice', 'Facturas', 'Facturacion', 'billing', 110),
    ('level', 'Niveles', 'Configuracion', 'settings', 850),
    ('location', 'Ubicaciones', 'Inventario', 'inventory', 220),
    ('location_type', 'Tipos de ubicacion', 'Inventario', 'inventory', 230),
    ('material', 'Materiales', 'Inventario', 'inventory', 240),
    ('material_component', 'Componentes', 'Inventario', 'inventory', 260),
    ('movement', 'Movimientos', 'Inventario', 'inventory', 250),
    ('payroll_concept', 'Conceptos', 'Recursos humanos', 'hr', 720),
    ('payroll_detail', 'Detalle', 'Recursos humanos', 'hr', 740),
    ('payroll_movement', 'Movimientos', 'Recursos humanos', 'hr', 730),
    ('payroll_period', 'Periodos de nomina', 'Recursos humanos', 'hr', 710),
    ('permission', 'Perfiles', 'Configuracion', 'settings', 920),
    ('pos_admin', 'Admin del punto de venta', 'Punto de venta', 'pos', 640),
    ('pos_terminal', 'Caja del punto de venta', 'Punto de venta', 'pos', 640),
    ('product', 'Productos', 'Inventario', 'inventory', 210),
    ('product_family', 'Familias de producto', 'Inventario', 'inventory', 212),
    ('proyect', 'Proyectos', 'Operaciones', 'operations', 310),
    ('restaurant_admin', 'Admin del restaurante', 'Restaurante', 'restaurant', 590),
    ('restaurant_cashier', 'Caja', 'Restaurante', 'restaurant', 590),
    ('restaurant_kitchen', 'Cocina', 'Restaurante', 'restaurant', 590),
    ('restaurant_waiter', 'Meseros', 'Restaurante', 'restaurant', 590),
    ('subdepartment', 'Subdepartamentos', 'Configuracion', 'settings', 840),
    ('task', 'Tareas', 'Operaciones', 'operations', 320),
    ('task_note', 'Notas de tarea', 'Operaciones', 'operations', 330),
    ('task_type', 'Tipos de tarea', 'Operaciones', 'operations', 340),
    ('ticket', 'Tickets', 'Facturacion', 'billing', 160),
    ('unit', 'Unidades', 'Inventario', 'inventory', 216),
    ('user', 'Usuarios', 'Configuracion', 'settings', 910)
) AS c (entidad, etiqueta, grupo, icono, orden)
WHERE ep.entity_name = c.entidad
  AND ep.deletion_date IS NULL
  AND ep.menu_label IS NULL;

-- 2. Dar de alta los pares (rol, catalogo) que faltan, con el mismo acceso que
--    el rol ya tiene sobre `product`.
--
--    Se copia de `product` en lugar de escribir un numero: el rol que captura
--    productos tiene que poder capturar la familia a la que los mete, y el que
--    solo los consulta solo consulta la familia. Un valor fijo aqui le daria
--    alta de catalogos a quien no captura, o se lo negaria a quien si.
--
--    Solo los tres catalogos de los que cuelga un producto. El resto de los
--    pares que falten los siembra la matriz, que es su trabajo.
INSERT INTO entity_permission (
    id_permission, entity_name, control_type, menu_location,
    menu_group, menu_group_icon, menu_label, menu_order, created_by
)
SELECT p.id_permission, c.entidad, p.control_type, 'sidebar',
       'Inventario', 'inventory', c.etiqueta, c.orden, 1
FROM entity_permission p
CROSS JOIN (VALUES
    ('product_family', 'Familias de producto', 212),
    ('brand',          'Marcas',               214),
    ('unit',           'Unidades',             216)
) AS c (entidad, etiqueta, orden)
WHERE p.entity_name = 'product'
  AND p.deletion_date IS NULL
-- El gestor manda: si el par ya existe -vivo o retirado a proposito- no se
-- toca. `ON CONFLICT DO NOTHING` cubre el vivo; este NOT EXISTS cubre el
-- retirado, que de otro modo resucitaria un acceso que alguien quito.
  AND NOT EXISTS (
      SELECT 1 FROM entity_permission x
      WHERE x.id_permission = p.id_permission
        AND x.entity_name = c.entidad
  )
ON CONFLICT (id_permission, entity_name) DO NOTHING;

COMMIT;
