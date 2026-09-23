-- Permisos por modulo y accion CRUD. GENERADO por
-- backend/scripts/seed_module_permissions.py desde app/modules/registry.py.
-- No editar a mano: el registro es la fuente de verdad y cualquier cambio aqui
-- se pierde en la siguiente generacion.
--
-- Que cambia respecto al sembrado anterior
-- ----------------------------------------
-- Las entidades se agrupaban en dominios inventados al momento -catalogos,
-- comercial, encuestas- que no coincidian con los modulos del negocio. Ahora
-- cada entidad pertenece a exactamente un modulo declarado, y el registro se
-- niega a cargar si alguna queda fuera o en dos.
--
-- Este sembrado SUSTITUYE lo anterior en lugar de rellenar huecos: conservar
-- dos criterios conviviendo es como aparecieron los descuadres previos. El
-- borrado es logico, asi que lo anterior queda para consulta.
--
-- Los tres almacenes viven en modulos distintos y no comparten tabla ni
-- servicio. Conceder `inventario` a un rol NO le da el almacen de logistica ni
-- el del restaurante.
--
-- 10 modulos, 12 roles, 11 capacidades,
-- 381 filas.
--
--   facturacion      9 entidades
--     Administrator (administrar), gerente_administrativo (capturar), vendedor (capturar), Gerente (capturar)
--   inventario      10 entidades  [almacen propio]
--     Administrator (administrar), gerente_administrativo (consultar), vendedor (consultar), Jefe de taller (consultar), Supervisor (consultar), Gerente (consultar), Almacenista (capturar), Jefe de almacen (administrar)
--   operaciones     10 entidades
--     Administrator (administrar), gerente_administrativo (editar), Jefe de taller (capturar), Supervisor (capturar), Gerente (editar)
--   logistica       21 entidades  [almacen propio]
--     Administrator (administrar), gerente_administrativo (consultar), Gerente (consultar), Jefe de almacen (capturar)
--   restaurante      0 entidades  [almacen propio]
--     Administrator (administrar)
--   pos              0 entidades
--     Administrator (administrar)
--   crm              7 entidades
--     Administrator (administrar), gerente_administrativo (capturar), vendedor (capturar), Gerente (capturar)
--   rh               4 entidades
--     Administrator (administrar), gerente_administrativo (capturar), Gerente (consultar)
--   configuracion    5 entidades
--     Administrator (administrar), gerente_administrativo (consultar), vendedor (consultar), Mesero (consultar), Cocina (consultar), Caja Restaurante (consultar), Admin Restaurante (consultar), Jefe de taller (consultar), Supervisor (consultar), Gerente (consultar), Almacenista (consultar), Jefe de almacen (consultar)
--   seguridad        7 entidades
--     Administrator (administrar)

BEGIN;

-- NO se marca de baja lo vigente antes de sembrar.
--
-- Lo hacia, y corria en cada reinicio del pod, asi que revertia cualquier
-- ajuste del gestor de roles en el siguiente despliegue. La matriz que
-- gobierna hoy es 20260901000000, que ya siembra sin pisar; esta se conserva
-- por historia y se limita a insertar lo que falte.
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

INSERT INTO entity_permission (
    id_permission, entity_name, scope_create, scope_read, scope_update, scope_delete, menu_location,
    menu_group, menu_group_icon, menu_label, menu_order, created_by
)
SELECT v.id_permission, v.entity_name, v.scope_create, v.scope_read, v.scope_update, v.scope_delete, v.menu_location,
       v.menu_group, v.menu_group_icon, v.menu_label, v.menu_order, 1
FROM (VALUES
    (1, 'department', 4, 4, 4, 4, 'sidebar', 'Configuracion', 'settings', 'Departamentos', 830),   -- Administrator / administrar
    (1, 'level', 4, 4, 4, 4, 'sidebar', 'Configuracion', 'settings', 'Niveles', 850),   -- Administrator / administrar
    (1, 'status', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 890),   -- Administrator / administrar
    (1, 'subdepartment', 4, 4, 4, 4, 'sidebar', 'Configuracion', 'settings', 'Subdepartamentos', 840),   -- Administrator / administrar
    (1, 'theme', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 890),   -- Administrator / administrar
    (1, 'appointment', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 690),   -- Administrator / administrar
    (1, 'customer_supplier', 4, 4, 4, 4, 'sidebar', 'CRM', 'crm', 'Clientes y proveedores', 620),   -- Administrator / administrar
    (1, 'nm_survey_user', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 690),   -- Administrator / administrar
    (1, 'product_sale_config', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 690),   -- Administrator / administrar
    (1, 'public_api_key', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 690),   -- Administrator / administrar
    (1, 'survey_multiple_answer', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 690),   -- Administrator / administrar
    (1, 'survey_question', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 690),   -- Administrator / administrar
    (1, 'bank', 4, 4, 4, 4, 'sidebar', 'Facturacion', 'billing', 'Bancos', 140),   -- Administrator / administrar
    (1, 'bank_account', 4, 4, 4, 4, 'sidebar', 'Facturacion', 'billing', 'Cuentas bancarias', 150),   -- Administrator / administrar
    (1, 'fiscal_account', 4, 4, 4, 4, 'sidebar', 'Facturacion', 'billing', 'Cuentas fiscales', 130),   -- Administrator / administrar
    (1, 'fiscal_record', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 190),   -- Administrator / administrar
    (1, 'fiscal_stamp', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 190),   -- Administrator / administrar
    (1, 'invoice', 4, 4, 4, 4, 'sidebar', 'Facturacion', 'billing', 'Facturas', 110),   -- Administrator / administrar
    (1, 'invoice_material_service', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 190),   -- Administrator / administrar
    (1, 'service', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 190),   -- Administrator / administrar
    (1, 'ticket', 4, 4, 4, 4, 'sidebar', 'Facturacion', 'billing', 'Tickets', 160),   -- Administrator / administrar
    (1, 'brand', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 290),   -- Administrator / administrar
    (1, 'inventory_status', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 290),   -- Administrator / administrar
    (1, 'location', 4, 4, 4, 4, 'sidebar', 'Inventario', 'inventory', 'Ubicaciones', 220),   -- Administrator / administrar
    (1, 'location_type', 4, 4, 4, 4, 'sidebar', 'Inventario', 'inventory', 'Tipos de ubicacion', 230),   -- Administrator / administrar
    (1, 'material', 4, 4, 4, 4, 'sidebar', 'Inventario', 'inventory', 'Materiales', 240),   -- Administrator / administrar
    (1, 'material_component', 4, 4, 4, 4, 'sidebar', 'Inventario', 'inventory', 'Componentes', 260),   -- Administrator / administrar
    (1, 'movement', 4, 4, 4, 4, 'sidebar', 'Inventario', 'inventory', 'Movimientos', 250),   -- Administrator / administrar
    (1, 'product', 4, 4, 4, 4, 'sidebar', 'Inventario', 'inventory', 'Productos', 210),   -- Administrator / administrar
    (1, 'product_family', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 290),   -- Administrator / administrar
    (1, 'unit', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 290),   -- Administrator / administrar
    (1, 'logistics_address', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 490),   -- Administrator / administrar
    (1, 'logistics_branch', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 490),   -- Administrator / administrar
    (1, 'logistics_contact', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 490),   -- Administrator / administrar
    (1, 'logistics_contract', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 490),   -- Administrator / administrar
    (1, 'logistics_evidence', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 490),   -- Administrator / administrar
    (1, 'logistics_file', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 490),   -- Administrator / administrar
    (1, 'logistics_incident', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 490),   -- Administrator / administrar
    (1, 'logistics_inventory', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 490),   -- Administrator / administrar
    (1, 'logistics_location', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 490),   -- Administrator / administrar
    (1, 'logistics_maintenance', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 490),   -- Administrator / administrar
    (1, 'logistics_operator', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 490),   -- Administrator / administrar
    (1, 'logistics_quotation', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 490),   -- Administrator / administrar
    (1, 'logistics_rack', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 490),   -- Administrator / administrar
    (1, 'logistics_rate', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 490),   -- Administrator / administrar
    (1, 'logistics_receivable', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 490),   -- Administrator / administrar
    (1, 'logistics_service_request', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 490),   -- Administrator / administrar
    (1, 'logistics_shipment', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 490),   -- Administrator / administrar
    (1, 'logistics_trailer', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 490),   -- Administrator / administrar
    (1, 'logistics_trip', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 490),   -- Administrator / administrar
    (1, 'logistics_unit', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 490),   -- Administrator / administrar
    (1, 'logistics_warehouse', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 490),   -- Administrator / administrar
    (1, 'incident', 4, 4, 4, 4, 'sidebar', 'Operaciones', 'operations', 'Incidencias', 350),   -- Administrator / administrar
    (1, 'incident_detail', 4, 4, 4, 4, 'sidebar', 'Operaciones', 'operations', 'Detalle de incidencias', 360),   -- Administrator / administrar
    (1, 'incident_type', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 390),   -- Administrator / administrar
    (1, 'nm_incident_product', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 390),   -- Administrator / administrar
    (1, 'nm_template_task', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 390),   -- Administrator / administrar
    (1, 'proyect', 4, 4, 4, 4, 'sidebar', 'Operaciones', 'operations', 'Proyectos', 310),   -- Administrator / administrar
    (1, 'task', 4, 4, 4, 4, 'sidebar', 'Operaciones', 'operations', 'Tareas', 320),   -- Administrator / administrar
    (1, 'task_note', 4, 4, 4, 4, 'sidebar', 'Operaciones', 'operations', 'Notas de tarea', 330),   -- Administrator / administrar
    (1, 'task_type', 4, 4, 4, 4, 'sidebar', 'Operaciones', 'operations', 'Tipos de tarea', 340),   -- Administrator / administrar
    (1, 'template', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 390),   -- Administrator / administrar
    (1, 'payroll_concept', 4, 4, 4, 4, 'sidebar', 'Recursos humanos', 'hr', 'Conceptos', 720),   -- Administrator / administrar
    (1, 'payroll_detail', 4, 4, 4, 4, 'sidebar', 'Recursos humanos', 'hr', 'Detalle', 740),   -- Administrator / administrar
    (1, 'payroll_movement', 4, 4, 4, 4, 'sidebar', 'Recursos humanos', 'hr', 'Movimientos', 730),   -- Administrator / administrar
    (1, 'payroll_period', 4, 4, 4, 4, 'sidebar', 'Recursos humanos', 'hr', 'Periodos de nomina', 710),   -- Administrator / administrar
    (1, 'entity_permission', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 990),   -- Administrator / administrar
    (1, 'field', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 990),   -- Administrator / administrar
    (1, 'nm_field_permission', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 990),   -- Administrator / administrar
    (1, 'permission', 4, 4, 4, 4, 'sidebar', 'Seguridad', 'security', 'Perfiles', 920),   -- Administrator / administrar
    (1, 'user', 4, 4, 4, 4, 'sidebar', 'Seguridad', 'security', 'Usuarios', 910),   -- Administrator / administrar
    (1, 'incident_supervision', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 390),   -- Administrator / consultar
    (1, 'inventory_adjustment', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 290),   -- Administrator / consultar
    (1, 'kronos_device', 0, 4, 0, 0, 'settings', NULL, NULL, NULL, 790),   -- Administrator / consultar
    (1, 'pos_admin', 4, 4, 4, 4, 'sidebar', 'Punto de venta', 'pos', 'Admin del punto de venta', 640),   -- Administrator / administrar
    (1, 'pos_terminal', 4, 4, 4, 0, 'sidebar', 'Punto de venta', 'pos', 'Caja del punto de venta', 640),   -- Administrator / capturar
    (1, 'project_authorization', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 390),   -- Administrator / consultar
    (1, 'project_execution', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 390),   -- Administrator / consultar
    (1, 'restaurant_admin', 4, 4, 4, 4, 'sidebar', 'Restaurante', 'restaurant', 'Admin del restaurante', 590),   -- Administrator / administrar
    (1, 'restaurant_cashier', 4, 4, 4, 0, 'sidebar', 'Restaurante', 'restaurant', 'Caja', 590),   -- Administrator / capturar
    (1, 'restaurant_kitchen', 0, 4, 4, 0, 'sidebar', 'Restaurante', 'restaurant', 'Cocina', 590),   -- Administrator / editar
    (1, 'restaurant_waiter', 4, 4, 4, 0, 'sidebar', 'Restaurante', 'restaurant', 'Meseros', 590),   -- Administrator / capturar
    (2, 'department', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Departamentos', 830),   -- gerente_administrativo / consultar
    (2, 'level', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Niveles', 850),   -- gerente_administrativo / consultar
    (2, 'status', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 890),   -- gerente_administrativo / consultar
    (2, 'subdepartment', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Subdepartamentos', 840),   -- gerente_administrativo / consultar
    (2, 'theme', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 890),   -- gerente_administrativo / consultar
    (2, 'appointment', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 690),   -- gerente_administrativo / capturar
    (2, 'customer_supplier', 4, 4, 4, 0, 'sidebar', 'CRM', 'crm', 'Clientes y proveedores', 620),   -- gerente_administrativo / capturar
    (2, 'nm_survey_user', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 690),   -- gerente_administrativo / capturar
    (2, 'product_sale_config', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 690),   -- gerente_administrativo / capturar
    (2, 'public_api_key', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 690),   -- gerente_administrativo / capturar
    (2, 'survey_multiple_answer', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 690),   -- gerente_administrativo / capturar
    (2, 'survey_question', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 690),   -- gerente_administrativo / capturar
    (2, 'bank', 4, 4, 4, 0, 'sidebar', 'Facturacion', 'billing', 'Bancos', 140),   -- gerente_administrativo / capturar
    (2, 'bank_account', 4, 4, 4, 0, 'sidebar', 'Facturacion', 'billing', 'Cuentas bancarias', 150),   -- gerente_administrativo / capturar
    (2, 'fiscal_account', 4, 4, 4, 0, 'sidebar', 'Facturacion', 'billing', 'Cuentas fiscales', 130),   -- gerente_administrativo / capturar
    (2, 'fiscal_record', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 190),   -- gerente_administrativo / capturar
    (2, 'fiscal_stamp', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 190),   -- gerente_administrativo / capturar
    (2, 'invoice', 4, 4, 4, 0, 'sidebar', 'Facturacion', 'billing', 'Facturas', 110),   -- gerente_administrativo / capturar
    (2, 'invoice_material_service', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 190),   -- gerente_administrativo / capturar
    (2, 'service', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 190),   -- gerente_administrativo / capturar
    (2, 'ticket', 4, 4, 4, 0, 'sidebar', 'Facturacion', 'billing', 'Tickets', 160),   -- gerente_administrativo / capturar
    (2, 'brand', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 290),   -- gerente_administrativo / consultar
    (2, 'inventory_status', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 290),   -- gerente_administrativo / consultar
    (2, 'location', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Ubicaciones', 220),   -- gerente_administrativo / consultar
    (2, 'location_type', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Tipos de ubicacion', 230),   -- gerente_administrativo / consultar
    (2, 'material', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Materiales', 240),   -- gerente_administrativo / consultar
    (2, 'material_component', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Componentes', 260),   -- gerente_administrativo / consultar
    (2, 'movement', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Movimientos', 250),   -- gerente_administrativo / consultar
    (2, 'product', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Productos', 210),   -- gerente_administrativo / consultar
    (2, 'product_family', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 290),   -- gerente_administrativo / consultar
    (2, 'unit', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 290),   -- gerente_administrativo / consultar
    (2, 'logistics_address', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490),   -- gerente_administrativo / consultar
    (2, 'logistics_branch', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490),   -- gerente_administrativo / consultar
    (2, 'logistics_contact', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490),   -- gerente_administrativo / consultar
    (2, 'logistics_contract', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490),   -- gerente_administrativo / consultar
    (2, 'logistics_evidence', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490),   -- gerente_administrativo / consultar
    (2, 'logistics_file', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490),   -- gerente_administrativo / consultar
    (2, 'logistics_incident', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490),   -- gerente_administrativo / consultar
    (2, 'logistics_inventory', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490),   -- gerente_administrativo / consultar
    (2, 'logistics_location', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490),   -- gerente_administrativo / consultar
    (2, 'logistics_maintenance', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490),   -- gerente_administrativo / consultar
    (2, 'logistics_operator', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490),   -- gerente_administrativo / consultar
    (2, 'logistics_quotation', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490),   -- gerente_administrativo / consultar
    (2, 'logistics_rack', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490),   -- gerente_administrativo / consultar
    (2, 'logistics_rate', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490),   -- gerente_administrativo / consultar
    (2, 'logistics_receivable', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490),   -- gerente_administrativo / consultar
    (2, 'logistics_service_request', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490),   -- gerente_administrativo / consultar
    (2, 'logistics_shipment', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490),   -- gerente_administrativo / consultar
    (2, 'logistics_trailer', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490),   -- gerente_administrativo / consultar
    (2, 'logistics_trip', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490),   -- gerente_administrativo / consultar
    (2, 'logistics_unit', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490),   -- gerente_administrativo / consultar
    (2, 'logistics_warehouse', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490),   -- gerente_administrativo / consultar
    (2, 'incident', 0, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Incidencias', 350),   -- gerente_administrativo / editar
    (2, 'incident_detail', 0, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Detalle de incidencias', 360),   -- gerente_administrativo / editar
    (2, 'incident_type', 0, 4, 4, 0, 'hidden', NULL, NULL, NULL, 390),   -- gerente_administrativo / editar
    (2, 'nm_incident_product', 0, 4, 4, 0, 'hidden', NULL, NULL, NULL, 390),   -- gerente_administrativo / editar
    (2, 'nm_template_task', 0, 4, 4, 0, 'hidden', NULL, NULL, NULL, 390),   -- gerente_administrativo / editar
    (2, 'proyect', 0, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Proyectos', 310),   -- gerente_administrativo / editar
    (2, 'task', 0, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Tareas', 320),   -- gerente_administrativo / editar
    (2, 'task_note', 0, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Notas de tarea', 330),   -- gerente_administrativo / editar
    (2, 'task_type', 0, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Tipos de tarea', 340),   -- gerente_administrativo / editar
    (2, 'template', 0, 4, 4, 0, 'hidden', NULL, NULL, NULL, 390),   -- gerente_administrativo / editar
    (2, 'payroll_concept', 4, 4, 4, 0, 'sidebar', 'Recursos humanos', 'hr', 'Conceptos', 720),   -- gerente_administrativo / capturar
    (2, 'payroll_detail', 4, 4, 4, 0, 'sidebar', 'Recursos humanos', 'hr', 'Detalle', 740),   -- gerente_administrativo / capturar
    (2, 'payroll_movement', 4, 4, 4, 0, 'sidebar', 'Recursos humanos', 'hr', 'Movimientos', 730),   -- gerente_administrativo / capturar
    (2, 'payroll_period', 4, 4, 4, 0, 'sidebar', 'Recursos humanos', 'hr', 'Periodos de nomina', 710),   -- gerente_administrativo / capturar
    (2, 'incident_supervision', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 390),   -- gerente_administrativo / consultar
    (2, 'kronos_device', 0, 4, 0, 0, 'settings', NULL, NULL, NULL, 790),   -- gerente_administrativo / consultar
    (3, 'department', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Departamentos', 830),   -- vendedor / consultar
    (3, 'level', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Niveles', 850),   -- vendedor / consultar
    (3, 'status', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 890),   -- vendedor / consultar
    (3, 'subdepartment', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Subdepartamentos', 840),   -- vendedor / consultar
    (3, 'theme', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 890),   -- vendedor / consultar
    (3, 'appointment', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 690),   -- vendedor / capturar
    (3, 'customer_supplier', 4, 4, 4, 0, 'sidebar', 'CRM', 'crm', 'Clientes y proveedores', 620),   -- vendedor / capturar
    (3, 'nm_survey_user', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 690),   -- vendedor / capturar
    (3, 'product_sale_config', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 690),   -- vendedor / capturar
    (3, 'public_api_key', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 690),   -- vendedor / capturar
    (3, 'survey_multiple_answer', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 690),   -- vendedor / capturar
    (3, 'survey_question', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 690),   -- vendedor / capturar
    (3, 'bank', 4, 4, 4, 0, 'sidebar', 'Facturacion', 'billing', 'Bancos', 140),   -- vendedor / capturar
    (3, 'bank_account', 4, 4, 4, 0, 'sidebar', 'Facturacion', 'billing', 'Cuentas bancarias', 150),   -- vendedor / capturar
    (3, 'fiscal_account', 4, 4, 4, 0, 'sidebar', 'Facturacion', 'billing', 'Cuentas fiscales', 130),   -- vendedor / capturar
    (3, 'fiscal_record', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 190),   -- vendedor / capturar
    (3, 'fiscal_stamp', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 190),   -- vendedor / capturar
    (3, 'invoice', 4, 4, 4, 0, 'sidebar', 'Facturacion', 'billing', 'Facturas', 110),   -- vendedor / capturar
    (3, 'invoice_material_service', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 190),   -- vendedor / capturar
    (3, 'service', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 190),   -- vendedor / capturar
    (3, 'ticket', 4, 4, 4, 0, 'sidebar', 'Facturacion', 'billing', 'Tickets', 160),   -- vendedor / capturar
    (3, 'brand', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 290),   -- vendedor / consultar
    (3, 'inventory_status', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 290),   -- vendedor / consultar
    (3, 'location', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Ubicaciones', 220),   -- vendedor / consultar
    (3, 'location_type', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Tipos de ubicacion', 230),   -- vendedor / consultar
    (3, 'material', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Materiales', 240),   -- vendedor / consultar
    (3, 'material_component', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Componentes', 260),   -- vendedor / consultar
    (3, 'movement', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Movimientos', 250),   -- vendedor / consultar
    (3, 'product', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Productos', 210),   -- vendedor / consultar
    (3, 'product_family', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 290),   -- vendedor / consultar
    (3, 'unit', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 290),   -- vendedor / consultar
    (10, 'department', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Departamentos', 830),   -- Mesero / consultar
    (10, 'level', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Niveles', 850),   -- Mesero / consultar
    (10, 'status', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 890),   -- Mesero / consultar
    (10, 'subdepartment', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Subdepartamentos', 840),   -- Mesero / consultar
    (10, 'theme', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 890),   -- Mesero / consultar
    (10, 'restaurant_waiter', 4, 4, 4, 0, 'sidebar', 'Restaurante', 'restaurant', 'Meseros', 590),   -- Mesero / capturar
    (11, 'department', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Departamentos', 830),   -- Cocina / consultar
    (11, 'level', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Niveles', 850),   -- Cocina / consultar
    (11, 'status', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 890),   -- Cocina / consultar
    (11, 'subdepartment', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Subdepartamentos', 840),   -- Cocina / consultar
    (11, 'theme', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 890),   -- Cocina / consultar
    (11, 'restaurant_kitchen', 0, 4, 4, 0, 'sidebar', 'Restaurante', 'restaurant', 'Cocina', 590),   -- Cocina / editar
    (12, 'department', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Departamentos', 830),   -- Caja Restaurante / consultar
    (12, 'level', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Niveles', 850),   -- Caja Restaurante / consultar
    (12, 'status', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 890),   -- Caja Restaurante / consultar
    (12, 'subdepartment', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Subdepartamentos', 840),   -- Caja Restaurante / consultar
    (12, 'theme', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 890),   -- Caja Restaurante / consultar
    (12, 'restaurant_cashier', 4, 4, 4, 0, 'sidebar', 'Restaurante', 'restaurant', 'Caja', 590),   -- Caja Restaurante / capturar
    (13, 'department', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Departamentos', 830),   -- Admin Restaurante / consultar
    (13, 'level', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Niveles', 850),   -- Admin Restaurante / consultar
    (13, 'status', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 890),   -- Admin Restaurante / consultar
    (13, 'subdepartment', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Subdepartamentos', 840),   -- Admin Restaurante / consultar
    (13, 'theme', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 890),   -- Admin Restaurante / consultar
    (13, 'restaurant_admin', 4, 4, 4, 4, 'sidebar', 'Restaurante', 'restaurant', 'Admin del restaurante', 590),   -- Admin Restaurante / administrar
    (13, 'restaurant_cashier', 4, 4, 4, 0, 'sidebar', 'Restaurante', 'restaurant', 'Caja', 590),   -- Admin Restaurante / capturar
    (13, 'restaurant_kitchen', 0, 4, 4, 0, 'sidebar', 'Restaurante', 'restaurant', 'Cocina', 590),   -- Admin Restaurante / editar
    (13, 'restaurant_waiter', 4, 4, 4, 0, 'sidebar', 'Restaurante', 'restaurant', 'Meseros', 590),   -- Admin Restaurante / capturar
    (14, 'department', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Departamentos', 830),   -- Jefe de taller / consultar
    (14, 'level', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Niveles', 850),   -- Jefe de taller / consultar
    (14, 'status', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 890),   -- Jefe de taller / consultar
    (14, 'subdepartment', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Subdepartamentos', 840),   -- Jefe de taller / consultar
    (14, 'theme', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 890),   -- Jefe de taller / consultar
    (14, 'brand', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 290),   -- Jefe de taller / consultar
    (14, 'inventory_status', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 290),   -- Jefe de taller / consultar
    (14, 'location', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Ubicaciones', 220),   -- Jefe de taller / consultar
    (14, 'location_type', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Tipos de ubicacion', 230),   -- Jefe de taller / consultar
    (14, 'material', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Materiales', 240),   -- Jefe de taller / consultar
    (14, 'material_component', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Componentes', 260),   -- Jefe de taller / consultar
    (14, 'movement', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Movimientos', 250),   -- Jefe de taller / consultar
    (14, 'product', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Productos', 210),   -- Jefe de taller / consultar
    (14, 'product_family', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 290),   -- Jefe de taller / consultar
    (14, 'unit', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 290),   -- Jefe de taller / consultar
    (14, 'incident', 4, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Incidencias', 350),   -- Jefe de taller / capturar
    (14, 'incident_detail', 4, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Detalle de incidencias', 360),   -- Jefe de taller / capturar
    (14, 'incident_type', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 390),   -- Jefe de taller / capturar
    (14, 'nm_incident_product', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 390),   -- Jefe de taller / capturar
    (14, 'nm_template_task', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 390),   -- Jefe de taller / capturar
    (14, 'proyect', 4, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Proyectos', 310),   -- Jefe de taller / capturar
    (14, 'task', 4, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Tareas', 320),   -- Jefe de taller / capturar
    (14, 'task_note', 4, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Notas de tarea', 330),   -- Jefe de taller / capturar
    (14, 'task_type', 4, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Tipos de tarea', 340),   -- Jefe de taller / capturar
    (14, 'template', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 390),   -- Jefe de taller / capturar
    (14, 'incident_supervision', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 390),   -- Jefe de taller / consultar
    (14, 'project_execution', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 390),   -- Jefe de taller / consultar
    (15, 'department', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Departamentos', 830),   -- Supervisor / consultar
    (15, 'level', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Niveles', 850),   -- Supervisor / consultar
    (15, 'status', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 890),   -- Supervisor / consultar
    (15, 'subdepartment', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Subdepartamentos', 840),   -- Supervisor / consultar
    (15, 'theme', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 890),   -- Supervisor / consultar
    (15, 'brand', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 290),   -- Supervisor / consultar
    (15, 'inventory_status', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 290),   -- Supervisor / consultar
    (15, 'location', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Ubicaciones', 220),   -- Supervisor / consultar
    (15, 'location_type', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Tipos de ubicacion', 230),   -- Supervisor / consultar
    (15, 'material', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Materiales', 240),   -- Supervisor / consultar
    (15, 'material_component', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Componentes', 260),   -- Supervisor / consultar
    (15, 'movement', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Movimientos', 250),   -- Supervisor / consultar
    (15, 'product', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Productos', 210),   -- Supervisor / consultar
    (15, 'product_family', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 290),   -- Supervisor / consultar
    (15, 'unit', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 290),   -- Supervisor / consultar
    (15, 'incident', 4, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Incidencias', 350),   -- Supervisor / capturar
    (15, 'incident_detail', 4, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Detalle de incidencias', 360),   -- Supervisor / capturar
    (15, 'incident_type', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 390),   -- Supervisor / capturar
    (15, 'nm_incident_product', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 390),   -- Supervisor / capturar
    (15, 'nm_template_task', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 390),   -- Supervisor / capturar
    (15, 'proyect', 4, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Proyectos', 310),   -- Supervisor / capturar
    (15, 'task', 4, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Tareas', 320),   -- Supervisor / capturar
    (15, 'task_note', 4, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Notas de tarea', 330),   -- Supervisor / capturar
    (15, 'task_type', 4, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Tipos de tarea', 340),   -- Supervisor / capturar
    (15, 'template', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 390),   -- Supervisor / capturar
    (15, 'incident_supervision', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 390),   -- Supervisor / consultar
    (16, 'department', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Departamentos', 830),   -- Gerente / consultar
    (16, 'level', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Niveles', 850),   -- Gerente / consultar
    (16, 'status', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 890),   -- Gerente / consultar
    (16, 'subdepartment', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Subdepartamentos', 840),   -- Gerente / consultar
    (16, 'theme', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 890),   -- Gerente / consultar
    (16, 'appointment', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 690),   -- Gerente / capturar
    (16, 'customer_supplier', 4, 4, 4, 0, 'sidebar', 'CRM', 'crm', 'Clientes y proveedores', 620),   -- Gerente / capturar
    (16, 'nm_survey_user', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 690),   -- Gerente / capturar
    (16, 'product_sale_config', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 690),   -- Gerente / capturar
    (16, 'public_api_key', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 690),   -- Gerente / capturar
    (16, 'survey_multiple_answer', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 690),   -- Gerente / capturar
    (16, 'survey_question', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 690),   -- Gerente / capturar
    (16, 'bank', 4, 4, 4, 0, 'sidebar', 'Facturacion', 'billing', 'Bancos', 140),   -- Gerente / capturar
    (16, 'bank_account', 4, 4, 4, 0, 'sidebar', 'Facturacion', 'billing', 'Cuentas bancarias', 150),   -- Gerente / capturar
    (16, 'fiscal_account', 4, 4, 4, 0, 'sidebar', 'Facturacion', 'billing', 'Cuentas fiscales', 130),   -- Gerente / capturar
    (16, 'fiscal_record', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 190),   -- Gerente / capturar
    (16, 'fiscal_stamp', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 190),   -- Gerente / capturar
    (16, 'invoice', 4, 4, 4, 0, 'sidebar', 'Facturacion', 'billing', 'Facturas', 110),   -- Gerente / capturar
    (16, 'invoice_material_service', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 190),   -- Gerente / capturar
    (16, 'service', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 190),   -- Gerente / capturar
    (16, 'ticket', 4, 4, 4, 0, 'sidebar', 'Facturacion', 'billing', 'Tickets', 160),   -- Gerente / capturar
    (16, 'brand', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 290),   -- Gerente / consultar
    (16, 'inventory_status', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 290),   -- Gerente / consultar
    (16, 'location', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Ubicaciones', 220),   -- Gerente / consultar
    (16, 'location_type', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Tipos de ubicacion', 230),   -- Gerente / consultar
    (16, 'material', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Materiales', 240),   -- Gerente / consultar
    (16, 'material_component', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Componentes', 260),   -- Gerente / consultar
    (16, 'movement', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Movimientos', 250),   -- Gerente / consultar
    (16, 'product', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Productos', 210),   -- Gerente / consultar
    (16, 'product_family', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 290),   -- Gerente / consultar
    (16, 'unit', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 290),   -- Gerente / consultar
    (16, 'logistics_address', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490),   -- Gerente / consultar
    (16, 'logistics_branch', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490),   -- Gerente / consultar
    (16, 'logistics_contact', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490),   -- Gerente / consultar
    (16, 'logistics_contract', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490),   -- Gerente / consultar
    (16, 'logistics_evidence', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490),   -- Gerente / consultar
    (16, 'logistics_file', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490),   -- Gerente / consultar
    (16, 'logistics_incident', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490),   -- Gerente / consultar
    (16, 'logistics_inventory', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490),   -- Gerente / consultar
    (16, 'logistics_location', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490),   -- Gerente / consultar
    (16, 'logistics_maintenance', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490),   -- Gerente / consultar
    (16, 'logistics_operator', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490),   -- Gerente / consultar
    (16, 'logistics_quotation', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490),   -- Gerente / consultar
    (16, 'logistics_rack', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490),   -- Gerente / consultar
    (16, 'logistics_rate', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490),   -- Gerente / consultar
    (16, 'logistics_receivable', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490),   -- Gerente / consultar
    (16, 'logistics_service_request', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490),   -- Gerente / consultar
    (16, 'logistics_shipment', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490),   -- Gerente / consultar
    (16, 'logistics_trailer', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490),   -- Gerente / consultar
    (16, 'logistics_trip', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490),   -- Gerente / consultar
    (16, 'logistics_unit', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490),   -- Gerente / consultar
    (16, 'logistics_warehouse', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490),   -- Gerente / consultar
    (16, 'incident', 0, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Incidencias', 350),   -- Gerente / editar
    (16, 'incident_detail', 0, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Detalle de incidencias', 360),   -- Gerente / editar
    (16, 'incident_type', 0, 4, 4, 0, 'hidden', NULL, NULL, NULL, 390),   -- Gerente / editar
    (16, 'nm_incident_product', 0, 4, 4, 0, 'hidden', NULL, NULL, NULL, 390),   -- Gerente / editar
    (16, 'nm_template_task', 0, 4, 4, 0, 'hidden', NULL, NULL, NULL, 390),   -- Gerente / editar
    (16, 'proyect', 0, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Proyectos', 310),   -- Gerente / editar
    (16, 'task', 0, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Tareas', 320),   -- Gerente / editar
    (16, 'task_note', 0, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Notas de tarea', 330),   -- Gerente / editar
    (16, 'task_type', 0, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Tipos de tarea', 340),   -- Gerente / editar
    (16, 'template', 0, 4, 4, 0, 'hidden', NULL, NULL, NULL, 390),   -- Gerente / editar
    (16, 'payroll_concept', 0, 4, 0, 0, 'sidebar', 'Recursos humanos', 'hr', 'Conceptos', 720),   -- Gerente / consultar
    (16, 'payroll_detail', 0, 4, 0, 0, 'sidebar', 'Recursos humanos', 'hr', 'Detalle', 740),   -- Gerente / consultar
    (16, 'payroll_movement', 0, 4, 0, 0, 'sidebar', 'Recursos humanos', 'hr', 'Movimientos', 730),   -- Gerente / consultar
    (16, 'payroll_period', 0, 4, 0, 0, 'sidebar', 'Recursos humanos', 'hr', 'Periodos de nomina', 710),   -- Gerente / consultar
    (16, 'incident_supervision', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 390),   -- Gerente / consultar
    (16, 'project_authorization', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 390),   -- Gerente / consultar
    (17, 'department', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Departamentos', 830),   -- Almacenista / consultar
    (17, 'level', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Niveles', 850),   -- Almacenista / consultar
    (17, 'status', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 890),   -- Almacenista / consultar
    (17, 'subdepartment', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Subdepartamentos', 840),   -- Almacenista / consultar
    (17, 'theme', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 890),   -- Almacenista / consultar
    (17, 'brand', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 290),   -- Almacenista / capturar
    (17, 'inventory_status', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 290),   -- Almacenista / capturar
    (17, 'location', 4, 4, 4, 0, 'sidebar', 'Inventario', 'inventory', 'Ubicaciones', 220),   -- Almacenista / capturar
    (17, 'location_type', 4, 4, 4, 0, 'sidebar', 'Inventario', 'inventory', 'Tipos de ubicacion', 230),   -- Almacenista / capturar
    (17, 'material', 4, 4, 4, 0, 'sidebar', 'Inventario', 'inventory', 'Materiales', 240),   -- Almacenista / capturar
    (17, 'material_component', 4, 4, 4, 0, 'sidebar', 'Inventario', 'inventory', 'Componentes', 260),   -- Almacenista / capturar
    (17, 'movement', 4, 4, 4, 0, 'sidebar', 'Inventario', 'inventory', 'Movimientos', 250),   -- Almacenista / capturar
    (17, 'product', 4, 4, 4, 0, 'sidebar', 'Inventario', 'inventory', 'Productos', 210),   -- Almacenista / capturar
    (17, 'product_family', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 290),   -- Almacenista / capturar
    (17, 'unit', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 290),   -- Almacenista / capturar
    (18, 'department', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Departamentos', 830),   -- Jefe de almacen / consultar
    (18, 'level', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Niveles', 850),   -- Jefe de almacen / consultar
    (18, 'status', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 890),   -- Jefe de almacen / consultar
    (18, 'subdepartment', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Subdepartamentos', 840),   -- Jefe de almacen / consultar
    (18, 'theme', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 890),   -- Jefe de almacen / consultar
    (18, 'brand', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 290),   -- Jefe de almacen / administrar
    (18, 'inventory_status', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 290),   -- Jefe de almacen / administrar
    (18, 'location', 4, 4, 4, 4, 'sidebar', 'Inventario', 'inventory', 'Ubicaciones', 220),   -- Jefe de almacen / administrar
    (18, 'location_type', 4, 4, 4, 4, 'sidebar', 'Inventario', 'inventory', 'Tipos de ubicacion', 230),   -- Jefe de almacen / administrar
    (18, 'material', 4, 4, 4, 4, 'sidebar', 'Inventario', 'inventory', 'Materiales', 240),   -- Jefe de almacen / administrar
    (18, 'material_component', 4, 4, 4, 4, 'sidebar', 'Inventario', 'inventory', 'Componentes', 260),   -- Jefe de almacen / administrar
    (18, 'movement', 4, 4, 4, 4, 'sidebar', 'Inventario', 'inventory', 'Movimientos', 250),   -- Jefe de almacen / administrar
    (18, 'product', 4, 4, 4, 4, 'sidebar', 'Inventario', 'inventory', 'Productos', 210),   -- Jefe de almacen / administrar
    (18, 'product_family', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 290),   -- Jefe de almacen / administrar
    (18, 'unit', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 290),   -- Jefe de almacen / administrar
    (18, 'logistics_address', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 490),   -- Jefe de almacen / capturar
    (18, 'logistics_branch', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 490),   -- Jefe de almacen / capturar
    (18, 'logistics_contact', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 490),   -- Jefe de almacen / capturar
    (18, 'logistics_contract', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 490),   -- Jefe de almacen / capturar
    (18, 'logistics_evidence', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 490),   -- Jefe de almacen / capturar
    (18, 'logistics_file', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 490),   -- Jefe de almacen / capturar
    (18, 'logistics_incident', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 490),   -- Jefe de almacen / capturar
    (18, 'logistics_inventory', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 490),   -- Jefe de almacen / capturar
    (18, 'logistics_location', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 490),   -- Jefe de almacen / capturar
    (18, 'logistics_maintenance', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 490),   -- Jefe de almacen / capturar
    (18, 'logistics_operator', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 490),   -- Jefe de almacen / capturar
    (18, 'logistics_quotation', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 490),   -- Jefe de almacen / capturar
    (18, 'logistics_rack', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 490),   -- Jefe de almacen / capturar
    (18, 'logistics_rate', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 490),   -- Jefe de almacen / capturar
    (18, 'logistics_receivable', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 490),   -- Jefe de almacen / capturar
    (18, 'logistics_service_request', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 490),   -- Jefe de almacen / capturar
    (18, 'logistics_shipment', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 490),   -- Jefe de almacen / capturar
    (18, 'logistics_trailer', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 490),   -- Jefe de almacen / capturar
    (18, 'logistics_trip', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 490),   -- Jefe de almacen / capturar
    (18, 'logistics_unit', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 490),   -- Jefe de almacen / capturar
    (18, 'logistics_warehouse', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 490),   -- Jefe de almacen / capturar
    (18, 'inventory_adjustment', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 290)   -- Jefe de almacen / consultar
) AS v (id_permission, entity_name, scope_create, scope_read, scope_update, scope_delete, menu_location,
        menu_group, menu_group_icon, menu_label, menu_order)
WHERE EXISTS (SELECT 1 FROM permission p WHERE p.id_permission = v.id_permission)
-- La restriccion unica es por (perfil, entidad) sin importar la baja logica, asi
-- que se reactiva la fila en lugar de insertar una segunda.
-- El gestor manda: aqui NO se pisa la fila que ya existe.
--
-- Una fila viva es del administrador y pisarla revierte su trabajo; una de baja
-- significa que la quito a proposito, y reactivarla devolveria un acceso
-- retirado. El registro solo da el valor por omision al par (perfil, entidad)
-- que todavia no existe.
ON CONFLICT (id_permission, entity_name) DO NOTHING;

END IF;
END $$;

-- Los permisos de campo se derivan del permiso de entidad, asi que hay que
-- rehacerlos: un modulo que cambio de alcance arrastra sus campos. Se dan de
-- baja los que quedaron sin respaldo y se derivan los que faltan.
UPDATE nm_field_permission nfp
   SET deletion_date = now()
 WHERE nfp.deletion_date IS NULL
   AND NOT EXISTS (
     SELECT 1
       FROM entity_permission ep
       JOIN field f ON f.id_field = nfp.id_field
      WHERE ep.id_permission = nfp.id_permission
        AND ep.entity_name = f.table_name
        AND ep.deletion_date IS NULL
   );

-- Guardado igual que el INSERT de arriba: la fuente de este INSERT lee
-- entity_permission.scope_*, que todavia no existe en la primera pasada.
DO $$
BEGIN
IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'entity_permission' AND column_name = 'scope_create'
) THEN

INSERT INTO nm_field_permission (id_field, id_permission, control_type, created_by)
-- Se hereda el alcance que el rol ya tiene sobre la entidad, recompuesto como
-- bitmask (1 crear, 2 leer, 4 actualizar, 8 borrar) a partir de las cuatro
-- columnas scope_* (0 = sin acceso, distinto de 0 = con acceso) desde que
-- 20260914110000_equipos_y_alcance_por_accion.sql reemplazo
-- entity_permission.control_type.
SELECT f.id_field, ep.id_permission,
       LEAST(
           (CASE WHEN ep.scope_create <> 0 THEN 1 ELSE 0 END) +
           (CASE WHEN ep.scope_read   <> 0 THEN 2 ELSE 0 END) +
           (CASE WHEN ep.scope_update <> 0 THEN 4 ELSE 0 END) +
           (CASE WHEN ep.scope_delete <> 0 THEN 8 ELSE 0 END),
           15
       )::text,
       1
FROM entity_permission ep
JOIN field f
  ON f.table_name = ep.entity_name
 AND f.deletion_date IS NULL
WHERE ep.deletion_date IS NULL
  -- `created_by` lo fija el servicio con el usuario de la sesion: si fuera
  -- capturable, cualquiera podria atribuir un registro a otra persona.
  AND f.field_name <> 'created_by'
  AND NOT EXISTS (
    SELECT 1 FROM nm_field_permission nfp
    WHERE nfp.id_field = f.id_field
      AND nfp.id_permission = ep.id_permission
      AND nfp.deletion_date IS NULL
  );

END IF;
END $$;

COMMIT;
