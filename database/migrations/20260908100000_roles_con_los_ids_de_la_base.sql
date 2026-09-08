-- Los cinco roles del negocio, en los identificadores que manda la base.
--
-- El cruce, medido antes de arreglarlo
-- ------------------------------------
-- El registro nombraba estos roles en los ids 14..18 mientras la base los tiene
-- en 2..6, y en los ids 2 y 3 declaraba dos roles que la base no tiene:
--
--     id   la base dice        el registro concedia
--     ---  ------------------  ----------------------
--      2   Supervisor          gerente_administrativo
--      3   Gerente             vendedor
--      4   Jefe de taller      -
--      5   Almacenista         -
--      6   Jefe de almacen     -
--
-- Contado en filas de permiso vivas: Supervisor 73 -53 en el menu- y Gerente
-- 61 -42-, los dos mas abiertos del sistema despues de Administrator; Jefe de
-- taller 6 y Almacenista 11. Es decir, los dos roles que hay que restringir
-- eran los que mas veian, y los que tienen que trabajar no podian: el
-- almacenista no tenia ni la capacidad `warehouse_voucher`, asi que no podia
-- levantar un vale.
--
-- Por que esta migracion PISA y no solo agrega
-- --------------------------------------------
-- El sembrado normal -scripts/seed_module_permissions.py- usa
-- `ON CONFLICT DO NOTHING`: solo agrega lo que falta. Aqui el problema es al
-- contrario, las filas que hay conceden lo que no toca, asi que resembrar
-- dejaria las viejas y sumaria las nuevas.
--
-- Se decidio que manda la base, y con ello reescribir las concesiones para que
-- cada rol reciba la suya. Es la excepcion a "el gestor manda" y esta acotada:
--
--   * solo los ids 2..6. Administrator y los cuatro roles del restaurante no
--     se tocan;
--   * lo que se retira se retira en LOGICO -`deletion_date`-, asi que queda
--     para consulta y la operacion se puede revisar despues;
--   * los usuarios no se mueven de rol. Nadie cambia de `id_permission`: lo que
--     cambia es lo que cada rol concede.
--
-- Como queda
-- ----------
--     2  Supervisor           29 filas
--     3  Gerente              72 filas
--     4  Jefe de taller       29 filas
--     5  Almacenista          19 filas
--     6  Jefe de almacen      41 filas
--
-- Y las capacidades del flujo de vales, que no las tenia ningun rol salvo
-- Administrator: `warehouse_voucher` y `warehouse_voucher_confirm` para los dos
-- roles de almacen, `warehouse_prevoucher` para el supervisor -que pide
-- material pero no lo surte-.

BEGIN;

CREATE TEMP TABLE matriz_objetivo (
    id_permission INTEGER,
    entity_name VARCHAR(100),
    -- TEXT y no INTEGER: asi lo tiene `entity_permission.control_type` en la
    -- base -es un mapa de bits guardado como texto- y comparar un integer
    -- contra el revienta con "operator does not exist: text = integer".
    control_type TEXT,
    menu_location VARCHAR(20),
    menu_group VARCHAR(100),
    menu_group_icon VARCHAR(50),
    menu_label VARCHAR(100),
    menu_order INTEGER
) ON COMMIT DROP;

INSERT INTO matriz_objetivo VALUES
    (2, 'brand', 2, 'sidebar', 'Inventario', 'inventory', 'Marcas', 214),
    (2, 'department', 2, 'sidebar', 'Configuracion', 'settings', 'Departamentos', 830),
    (2, 'incident', 7, 'sidebar', 'Operaciones', 'operations', 'Incidencias', 330),
    (2, 'incident_detail', 7, 'sidebar', 'Operaciones', 'operations', 'Subtipos de incidencia', 334),
    (2, 'incident_supervision', 2, 'hidden', NULL, NULL, NULL, 390),
    (2, 'incident_type', 7, 'sidebar', 'Operaciones', 'operations', 'Tipos de incidencia', 332),
    (2, 'inventory_status', 2, 'sidebar', 'Inventario', 'inventory', 'Estado de inventario', 270),
    (2, 'level', 2, 'sidebar', 'Configuracion', 'settings', 'Niveles', 850),
    (2, 'location', 2, 'sidebar', 'Inventario', 'inventory', 'Ubicaciones', 220),
    (2, 'location_type', 2, 'sidebar', 'Inventario', 'inventory', 'Tipos de ubicacion', 230),
    (2, 'material', 2, 'sidebar', 'Inventario', 'inventory', 'Materiales', 240),
    (2, 'material_attribute', 2, 'hidden', NULL, NULL, NULL, 290),
    (2, 'material_component', 2, 'sidebar', 'Inventario', 'inventory', 'Componentes', 260),
    (2, 'material_type', 2, 'hidden', NULL, NULL, NULL, 290),
    (2, 'movement', 2, 'sidebar', 'Inventario', 'inventory', 'Movimientos', 250),
    (2, 'nm_incident_product', 7, 'hidden', NULL, NULL, NULL, 390),
    (2, 'nm_template_task', 7, 'hidden', NULL, NULL, NULL, 390),
    (2, 'product', 2, 'sidebar', 'Inventario', 'inventory', 'Productos', 210),
    (2, 'product_family', 2, 'sidebar', 'Inventario', 'inventory', 'Familias y tipos', 212),
    (2, 'proyect', 7, 'sidebar', 'Operaciones', 'operations', 'Proyectos', 310),
    (2, 'status', 2, 'hidden', NULL, NULL, NULL, 890),
    (2, 'subdepartment', 2, 'sidebar', 'Configuracion', 'settings', 'Subdepartamentos', 840),
    (2, 'task', 7, 'sidebar', 'Operaciones', 'operations', 'Tareas', 320),
    (2, 'task_note', 7, 'hidden', NULL, NULL, NULL, 390),
    (2, 'task_type', 7, 'sidebar', 'Operaciones', 'operations', 'Tipos de tarea', 342),
    (2, 'template', 7, 'sidebar', 'Operaciones', 'operations', 'Plantillas de tarea', 340),
    (2, 'theme', 2, 'hidden', NULL, NULL, NULL, 890),
    (2, 'unit', 2, 'sidebar', 'Inventario', 'inventory', 'Unidades', 216),
    (2, 'warehouse_prevoucher', 7, 'sidebar', 'Inventario', 'inventory', 'Prevales de material', 290),
    (3, 'appointment', 7, 'hidden', NULL, NULL, NULL, 690),
    (3, 'bank', 7, 'sidebar', 'Facturacion', 'billing', 'Bancos', 140),
    (3, 'bank_account', 7, 'sidebar', 'Facturacion', 'billing', 'Cuentas bancarias', 150),
    (3, 'brand', 2, 'sidebar', 'Inventario', 'inventory', 'Marcas', 214),
    (3, 'customer_supplier', 7, 'sidebar', 'CRM', 'crm', 'Clientes y proveedores', 620),
    (3, 'department', 2, 'sidebar', 'Configuracion', 'settings', 'Departamentos', 830),
    (3, 'fiscal_account', 7, 'sidebar', 'Facturacion', 'billing', 'Cuentas fiscales', 130),
    (3, 'fiscal_record', 7, 'hidden', NULL, NULL, NULL, 190),
    (3, 'fiscal_stamp', 7, 'hidden', NULL, NULL, NULL, 190),
    (3, 'incident', 6, 'sidebar', 'Operaciones', 'operations', 'Incidencias', 330),
    (3, 'incident_detail', 6, 'sidebar', 'Operaciones', 'operations', 'Subtipos de incidencia', 334),
    (3, 'incident_supervision', 2, 'hidden', NULL, NULL, NULL, 390),
    (3, 'incident_type', 6, 'sidebar', 'Operaciones', 'operations', 'Tipos de incidencia', 332),
    (3, 'inventory_status', 2, 'sidebar', 'Inventario', 'inventory', 'Estado de inventario', 270),
    (3, 'invoice', 7, 'sidebar', 'Facturacion', 'billing', 'Facturas', 110),
    (3, 'invoice_material_service', 7, 'hidden', NULL, NULL, NULL, 190),
    (3, 'level', 2, 'sidebar', 'Configuracion', 'settings', 'Niveles', 850),
    (3, 'location', 2, 'sidebar', 'Inventario', 'inventory', 'Ubicaciones', 220),
    (3, 'location_type', 2, 'sidebar', 'Inventario', 'inventory', 'Tipos de ubicacion', 230),
    (3, 'logistics_address', 2, 'hidden', NULL, NULL, NULL, 490),
    (3, 'logistics_branch', 2, 'hidden', NULL, NULL, NULL, 490),
    (3, 'logistics_contact', 2, 'hidden', NULL, NULL, NULL, 490),
    (3, 'logistics_contract', 2, 'hidden', NULL, NULL, NULL, 490),
    (3, 'logistics_evidence', 2, 'hidden', NULL, NULL, NULL, 490),
    (3, 'logistics_file', 2, 'hidden', NULL, NULL, NULL, 490),
    (3, 'logistics_incident', 2, 'hidden', NULL, NULL, NULL, 490),
    (3, 'logistics_inventory', 2, 'hidden', NULL, NULL, NULL, 490),
    (3, 'logistics_location', 2, 'hidden', NULL, NULL, NULL, 490),
    (3, 'logistics_maintenance', 2, 'hidden', NULL, NULL, NULL, 490),
    (3, 'logistics_operator', 2, 'hidden', NULL, NULL, NULL, 490),
    (3, 'logistics_quotation', 2, 'hidden', NULL, NULL, NULL, 490),
    (3, 'logistics_rack', 2, 'hidden', NULL, NULL, NULL, 490),
    (3, 'logistics_rate', 2, 'hidden', NULL, NULL, NULL, 490),
    (3, 'logistics_receivable', 2, 'hidden', NULL, NULL, NULL, 490),
    (3, 'logistics_service_request', 2, 'hidden', NULL, NULL, NULL, 490),
    (3, 'logistics_shipment', 2, 'hidden', NULL, NULL, NULL, 490),
    (3, 'logistics_trailer', 2, 'hidden', NULL, NULL, NULL, 490),
    (3, 'logistics_trip', 2, 'hidden', NULL, NULL, NULL, 490),
    (3, 'logistics_unit', 2, 'hidden', NULL, NULL, NULL, 490),
    (3, 'logistics_warehouse', 2, 'hidden', NULL, NULL, NULL, 490),
    (3, 'material', 2, 'sidebar', 'Inventario', 'inventory', 'Materiales', 240),
    (3, 'material_attribute', 2, 'hidden', NULL, NULL, NULL, 290),
    (3, 'material_component', 2, 'sidebar', 'Inventario', 'inventory', 'Componentes', 260),
    (3, 'material_type', 2, 'hidden', NULL, NULL, NULL, 290),
    (3, 'movement', 2, 'sidebar', 'Inventario', 'inventory', 'Movimientos', 250),
    (3, 'nm_incident_product', 6, 'hidden', NULL, NULL, NULL, 390),
    (3, 'nm_survey_user', 7, 'hidden', NULL, NULL, NULL, 690),
    (3, 'nm_template_task', 6, 'hidden', NULL, NULL, NULL, 390),
    (3, 'payroll_concept', 2, 'sidebar', 'Recursos humanos', 'hr', 'Conceptos', 720),
    (3, 'payroll_detail', 2, 'sidebar', 'Recursos humanos', 'hr', 'Detalle', 740),
    (3, 'payroll_movement', 2, 'sidebar', 'Recursos humanos', 'hr', 'Movimientos', 730),
    (3, 'payroll_period', 2, 'sidebar', 'Recursos humanos', 'hr', 'Periodos de nomina', 710),
    (3, 'pos_admin', 15, 'sidebar', 'Punto de venta', 'pos', 'Admin del punto de venta', 640),
    (3, 'pos_terminal', 7, 'sidebar', 'Punto de venta', 'pos', 'Caja del punto de venta', 640),
    (3, 'product', 2, 'sidebar', 'Inventario', 'inventory', 'Productos', 210),
    (3, 'product_family', 2, 'sidebar', 'Inventario', 'inventory', 'Familias y tipos', 212),
    (3, 'product_sale_config', 7, 'hidden', NULL, NULL, NULL, 690),
    (3, 'project_authorization', 2, 'hidden', NULL, NULL, NULL, 390),
    (3, 'proyect', 6, 'sidebar', 'Operaciones', 'operations', 'Proyectos', 310),
    (3, 'public_api_key', 7, 'hidden', NULL, NULL, NULL, 690),
    (3, 'service', 7, 'hidden', NULL, NULL, NULL, 190),
    (3, 'status', 2, 'hidden', NULL, NULL, NULL, 890),
    (3, 'subdepartment', 2, 'sidebar', 'Configuracion', 'settings', 'Subdepartamentos', 840),
    (3, 'survey_multiple_answer', 7, 'hidden', NULL, NULL, NULL, 690),
    (3, 'survey_question', 7, 'hidden', NULL, NULL, NULL, 690),
    (3, 'task', 6, 'sidebar', 'Operaciones', 'operations', 'Tareas', 320),
    (3, 'task_note', 6, 'hidden', NULL, NULL, NULL, 390),
    (3, 'task_type', 6, 'sidebar', 'Operaciones', 'operations', 'Tipos de tarea', 342),
    (3, 'template', 6, 'sidebar', 'Operaciones', 'operations', 'Plantillas de tarea', 340),
    (3, 'theme', 2, 'hidden', NULL, NULL, NULL, 890),
    (3, 'ticket', 7, 'sidebar', 'Facturacion', 'billing', 'Tickets', 160),
    (3, 'unit', 2, 'sidebar', 'Inventario', 'inventory', 'Unidades', 216),
    (4, 'brand', 2, 'sidebar', 'Inventario', 'inventory', 'Marcas', 214),
    (4, 'department', 2, 'sidebar', 'Configuracion', 'settings', 'Departamentos', 830),
    (4, 'incident', 7, 'sidebar', 'Operaciones', 'operations', 'Incidencias', 330),
    (4, 'incident_detail', 7, 'sidebar', 'Operaciones', 'operations', 'Subtipos de incidencia', 334),
    (4, 'incident_supervision', 2, 'hidden', NULL, NULL, NULL, 390),
    (4, 'incident_type', 7, 'sidebar', 'Operaciones', 'operations', 'Tipos de incidencia', 332),
    (4, 'inventory_status', 2, 'sidebar', 'Inventario', 'inventory', 'Estado de inventario', 270),
    (4, 'level', 2, 'sidebar', 'Configuracion', 'settings', 'Niveles', 850),
    (4, 'location', 2, 'sidebar', 'Inventario', 'inventory', 'Ubicaciones', 220),
    (4, 'location_type', 2, 'sidebar', 'Inventario', 'inventory', 'Tipos de ubicacion', 230),
    (4, 'material', 2, 'sidebar', 'Inventario', 'inventory', 'Materiales', 240),
    (4, 'material_attribute', 2, 'hidden', NULL, NULL, NULL, 290),
    (4, 'material_component', 2, 'sidebar', 'Inventario', 'inventory', 'Componentes', 260),
    (4, 'material_type', 2, 'hidden', NULL, NULL, NULL, 290),
    (4, 'movement', 2, 'sidebar', 'Inventario', 'inventory', 'Movimientos', 250),
    (4, 'nm_incident_product', 7, 'hidden', NULL, NULL, NULL, 390),
    (4, 'nm_template_task', 7, 'hidden', NULL, NULL, NULL, 390),
    (4, 'product', 2, 'sidebar', 'Inventario', 'inventory', 'Productos', 210),
    (4, 'product_family', 2, 'sidebar', 'Inventario', 'inventory', 'Familias y tipos', 212),
    (4, 'project_execution', 2, 'hidden', NULL, NULL, NULL, 390),
    (4, 'proyect', 7, 'sidebar', 'Operaciones', 'operations', 'Proyectos', 310),
    (4, 'status', 2, 'hidden', NULL, NULL, NULL, 890),
    (4, 'subdepartment', 2, 'sidebar', 'Configuracion', 'settings', 'Subdepartamentos', 840),
    (4, 'task', 7, 'sidebar', 'Operaciones', 'operations', 'Tareas', 320),
    (4, 'task_note', 7, 'hidden', NULL, NULL, NULL, 390),
    (4, 'task_type', 7, 'sidebar', 'Operaciones', 'operations', 'Tipos de tarea', 342),
    (4, 'template', 7, 'sidebar', 'Operaciones', 'operations', 'Plantillas de tarea', 340),
    (4, 'theme', 2, 'hidden', NULL, NULL, NULL, 890),
    (4, 'unit', 2, 'sidebar', 'Inventario', 'inventory', 'Unidades', 216),
    (5, 'brand', 7, 'sidebar', 'Inventario', 'inventory', 'Marcas', 214),
    (5, 'department', 2, 'sidebar', 'Configuracion', 'settings', 'Departamentos', 830),
    (5, 'inventory_status', 7, 'sidebar', 'Inventario', 'inventory', 'Estado de inventario', 270),
    (5, 'level', 2, 'sidebar', 'Configuracion', 'settings', 'Niveles', 850),
    (5, 'location', 7, 'sidebar', 'Inventario', 'inventory', 'Ubicaciones', 220),
    (5, 'location_type', 7, 'sidebar', 'Inventario', 'inventory', 'Tipos de ubicacion', 230),
    (5, 'material', 7, 'sidebar', 'Inventario', 'inventory', 'Materiales', 240),
    (5, 'material_attribute', 7, 'hidden', NULL, NULL, NULL, 290),
    (5, 'material_component', 7, 'sidebar', 'Inventario', 'inventory', 'Componentes', 260),
    (5, 'material_type', 7, 'hidden', NULL, NULL, NULL, 290),
    (5, 'movement', 7, 'sidebar', 'Inventario', 'inventory', 'Movimientos', 250),
    (5, 'product', 7, 'sidebar', 'Inventario', 'inventory', 'Productos', 210),
    (5, 'product_family', 7, 'sidebar', 'Inventario', 'inventory', 'Familias y tipos', 212),
    (5, 'status', 2, 'hidden', NULL, NULL, NULL, 890),
    (5, 'subdepartment', 2, 'sidebar', 'Configuracion', 'settings', 'Subdepartamentos', 840),
    (5, 'theme', 2, 'hidden', NULL, NULL, NULL, 890),
    (5, 'unit', 7, 'sidebar', 'Inventario', 'inventory', 'Unidades', 216),
    (5, 'warehouse_voucher', 7, 'sidebar', 'Inventario', 'inventory', 'Vales de almacen', 290),
    (5, 'warehouse_voucher_confirm', 2, 'hidden', NULL, NULL, NULL, 290),
    (6, 'brand', 15, 'sidebar', 'Inventario', 'inventory', 'Marcas', 214),
    (6, 'department', 2, 'sidebar', 'Configuracion', 'settings', 'Departamentos', 830),
    (6, 'inventory_adjustment', 2, 'hidden', NULL, NULL, NULL, 290),
    (6, 'inventory_status', 15, 'sidebar', 'Inventario', 'inventory', 'Estado de inventario', 270),
    (6, 'level', 2, 'sidebar', 'Configuracion', 'settings', 'Niveles', 850),
    (6, 'location', 15, 'sidebar', 'Inventario', 'inventory', 'Ubicaciones', 220),
    (6, 'location_type', 15, 'sidebar', 'Inventario', 'inventory', 'Tipos de ubicacion', 230),
    (6, 'logistics_address', 7, 'hidden', NULL, NULL, NULL, 490),
    (6, 'logistics_branch', 7, 'hidden', NULL, NULL, NULL, 490),
    (6, 'logistics_contact', 7, 'hidden', NULL, NULL, NULL, 490),
    (6, 'logistics_contract', 7, 'hidden', NULL, NULL, NULL, 490),
    (6, 'logistics_evidence', 7, 'hidden', NULL, NULL, NULL, 490),
    (6, 'logistics_file', 7, 'hidden', NULL, NULL, NULL, 490),
    (6, 'logistics_incident', 7, 'hidden', NULL, NULL, NULL, 490),
    (6, 'logistics_inventory', 7, 'hidden', NULL, NULL, NULL, 490),
    (6, 'logistics_location', 7, 'hidden', NULL, NULL, NULL, 490),
    (6, 'logistics_maintenance', 7, 'hidden', NULL, NULL, NULL, 490),
    (6, 'logistics_operator', 7, 'hidden', NULL, NULL, NULL, 490),
    (6, 'logistics_quotation', 7, 'hidden', NULL, NULL, NULL, 490),
    (6, 'logistics_rack', 7, 'hidden', NULL, NULL, NULL, 490),
    (6, 'logistics_rate', 7, 'hidden', NULL, NULL, NULL, 490),
    (6, 'logistics_receivable', 7, 'hidden', NULL, NULL, NULL, 490),
    (6, 'logistics_service_request', 7, 'hidden', NULL, NULL, NULL, 490),
    (6, 'logistics_shipment', 7, 'hidden', NULL, NULL, NULL, 490),
    (6, 'logistics_trailer', 7, 'hidden', NULL, NULL, NULL, 490),
    (6, 'logistics_trip', 7, 'hidden', NULL, NULL, NULL, 490),
    (6, 'logistics_unit', 7, 'hidden', NULL, NULL, NULL, 490),
    (6, 'logistics_warehouse', 7, 'hidden', NULL, NULL, NULL, 490),
    (6, 'material', 15, 'sidebar', 'Inventario', 'inventory', 'Materiales', 240),
    (6, 'material_attribute', 15, 'hidden', NULL, NULL, NULL, 290),
    (6, 'material_component', 15, 'sidebar', 'Inventario', 'inventory', 'Componentes', 260),
    (6, 'material_type', 15, 'hidden', NULL, NULL, NULL, 290),
    (6, 'movement', 15, 'sidebar', 'Inventario', 'inventory', 'Movimientos', 250),
    (6, 'product', 15, 'sidebar', 'Inventario', 'inventory', 'Productos', 210),
    (6, 'product_family', 15, 'sidebar', 'Inventario', 'inventory', 'Familias y tipos', 212),
    (6, 'status', 2, 'hidden', NULL, NULL, NULL, 890),
    (6, 'subdepartment', 2, 'sidebar', 'Configuracion', 'settings', 'Subdepartamentos', 840),
    (6, 'theme', 2, 'hidden', NULL, NULL, NULL, 890),
    (6, 'unit', 15, 'sidebar', 'Inventario', 'inventory', 'Unidades', 216),
    (6, 'warehouse_voucher', 7, 'sidebar', 'Inventario', 'inventory', 'Vales de almacen', 290),
    (6, 'warehouse_voucher_confirm', 2, 'hidden', NULL, NULL, NULL, 290);

-- 1. Lo que falta.
INSERT INTO entity_permission (
    id_permission, entity_name, control_type, menu_location,
    menu_group, menu_group_icon, menu_label, menu_order, created_by
)
SELECT m.id_permission, m.entity_name, m.control_type::text, m.menu_location,
       m.menu_group, m.menu_group_icon, m.menu_label, m.menu_order, 1
FROM matriz_objetivo m
WHERE NOT EXISTS (
    SELECT 1 FROM entity_permission e
    WHERE e.id_permission = m.id_permission
      AND e.entity_name = m.entity_name
);

-- 2. Lo que existe con otro valor. Es la correccion de fondo: aqui es donde
--    Supervisor deja de tener los bits del gerente administrativo.
UPDATE entity_permission e
   SET control_type = m.control_type::text,
       menu_location = m.menu_location,
       menu_group = m.menu_group,
       menu_group_icon = m.menu_group_icon,
       menu_label = m.menu_label,
       menu_order = m.menu_order,
       deletion_date = NULL,
       last_update_date = now()
  FROM matriz_objetivo m
 WHERE e.id_permission = m.id_permission
   AND e.entity_name = m.entity_name
   AND (
        e.control_type IS DISTINCT FROM m.control_type::text
     OR e.menu_location IS DISTINCT FROM m.menu_location
     OR e.menu_label IS DISTINCT FROM m.menu_label
     OR e.deletion_date IS NOT NULL
   );

-- 3. Lo que el rol ya no debe tener. En logico: queda para consulta.
UPDATE entity_permission e
   SET deletion_date = now(),
       last_update_date = now()
 WHERE e.id_permission IN (2, 3, 4, 5, 6)
   AND e.deletion_date IS NULL
   AND NOT EXISTS (
       SELECT 1 FROM matriz_objetivo m
       WHERE m.id_permission = e.id_permission
         AND m.entity_name = e.entity_name
   );

COMMIT;
