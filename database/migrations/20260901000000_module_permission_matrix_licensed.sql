-- Permisos por modulo y accion CRUD. GENERADO por
-- backend/scripts/seed_module_permissions.py desde app/modules/registry.py.
-- No editar a mano: el registro es la fuente de verdad y cualquier cambio aqui
-- se pierde en la siguiente generacion.
--
-- Licencia por modulo/cliente
-- ---------------------------
-- El proyecto se vende por modulo: un cliente contrata Facturacion y
-- Restaurante, otro ademas Multiemisor+CSD. Los modulos de infraestructura
-- ('configuracion', 'seguridad') van siempre, sin importar licencia -- sin ellos ni
-- login ni un select de catalogo funcionan. Todo lo demas (incluida una
-- capacidad marcada `licencia_independiente=True`, como multiemisor dentro de
-- facturacion) solo se siembra si su clave aparece en la variable de entorno
-- LICENSED_MODULES del cliente (separada por comas), leida via `psql -v
-- licensed_modules=...` -- ver k8s/base/backend.yaml.
--
-- LICENSED_MODULES vacia o sin definir se interpreta como "todos los modulos":
-- una instalacion que nunca configuro esta variable (los 3 ambientes reales
-- de hoy) sigue viendo exactamente lo mismo que antes de este cambio, hasta
-- que alguien la restrinja a proposito.
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

-- Se marca de baja todo lo vigente antes de sembrar. Sin esto quedarian filas
-- de la matriz anterior con criterios distintos, y no habria forma de saber
-- cual gobierna. Corre en cada reinicio del pod, asi que tambien es lo que
-- retira un modulo si LICENSED_MODULES cambia a algo mas restringido.
UPDATE entity_permission
   SET deletion_date = now()
 WHERE deletion_date IS NULL;

INSERT INTO entity_permission (
    id_permission, entity_name, control_type, menu_location,
    menu_group, menu_group_icon, menu_label, menu_order, created_by
)
SELECT v.id_permission, v.entity_name, v.control_type, v.menu_location,
       v.menu_group, v.menu_group_icon, v.menu_label, v.menu_order, 1
FROM (VALUES
    (1, 'department', 15, 'sidebar', 'Configuracion', 'settings', 'Departamentos', 830, 'configuracion'),   -- Administrator / administrar
    (1, 'level', 15, 'sidebar', 'Configuracion', 'settings', 'Niveles', 850, 'configuracion'),   -- Administrator / administrar
    (1, 'status', 15, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Administrator / administrar
    (1, 'subdepartment', 15, 'sidebar', 'Configuracion', 'settings', 'Subdepartamentos', 840, 'configuracion'),   -- Administrator / administrar
    (1, 'theme', 15, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Administrator / administrar
    (1, 'appointment', 15, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- Administrator / administrar
    (1, 'customer_supplier', 15, 'sidebar', 'CRM', 'crm', 'Clientes y proveedores', 620, 'crm'),   -- Administrator / administrar
    (1, 'nm_survey_user', 15, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- Administrator / administrar
    (1, 'product_sale_config', 15, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- Administrator / administrar
    (1, 'public_api_key', 15, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- Administrator / administrar
    (1, 'survey_multiple_answer', 15, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- Administrator / administrar
    (1, 'survey_question', 15, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- Administrator / administrar
    (1, 'bank', 15, 'sidebar', 'Facturacion', 'billing', 'Bancos', 140, 'facturacion'),   -- Administrator / administrar
    (1, 'bank_account', 15, 'sidebar', 'Facturacion', 'billing', 'Cuentas bancarias', 150, 'facturacion'),   -- Administrator / administrar
    (1, 'fiscal_account', 15, 'sidebar', 'Facturacion', 'billing', 'Cuentas fiscales', 130, 'facturacion'),   -- Administrator / administrar
    (1, 'fiscal_record', 15, 'hidden', NULL, NULL, NULL, 190, 'facturacion'),   -- Administrator / administrar
    (1, 'fiscal_stamp', 15, 'hidden', NULL, NULL, NULL, 190, 'facturacion'),   -- Administrator / administrar
    (1, 'invoice', 15, 'sidebar', 'Facturacion', 'billing', 'Facturas', 110, 'facturacion'),   -- Administrator / administrar
    (1, 'invoice_material_service', 15, 'hidden', NULL, NULL, NULL, 190, 'facturacion'),   -- Administrator / administrar
    (1, 'service', 15, 'hidden', NULL, NULL, NULL, 190, 'facturacion'),   -- Administrator / administrar
    (1, 'ticket', 15, 'sidebar', 'Facturacion', 'billing', 'Tickets', 160, 'facturacion'),   -- Administrator / administrar
    (1, 'brand', 15, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Administrator / administrar
    (1, 'inventory_status', 15, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Administrator / administrar
    (1, 'location', 15, 'sidebar', 'Inventario', 'inventory', 'Ubicaciones', 220, 'inventario'),   -- Administrator / administrar
    (1, 'location_type', 15, 'sidebar', 'Inventario', 'inventory', 'Tipos de ubicacion', 230, 'inventario'),   -- Administrator / administrar
    (1, 'material', 15, 'sidebar', 'Inventario', 'inventory', 'Materiales', 240, 'inventario'),   -- Administrator / administrar
    (1, 'material_component', 15, 'sidebar', 'Inventario', 'inventory', 'Componentes', 260, 'inventario'),   -- Administrator / administrar
    (1, 'movement', 15, 'sidebar', 'Inventario', 'inventory', 'Movimientos', 250, 'inventario'),   -- Administrator / administrar
    (1, 'product', 15, 'sidebar', 'Inventario', 'inventory', 'Productos', 210, 'inventario'),   -- Administrator / administrar
    (1, 'product_family', 15, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Administrator / administrar
    (1, 'unit', 15, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Administrator / administrar
    (1, 'logistics_address', 15, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Administrator / administrar
    (1, 'logistics_branch', 15, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Administrator / administrar
    (1, 'logistics_contact', 15, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Administrator / administrar
    (1, 'logistics_contract', 15, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Administrator / administrar
    (1, 'logistics_evidence', 15, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Administrator / administrar
    (1, 'logistics_file', 15, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Administrator / administrar
    (1, 'logistics_incident', 15, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Administrator / administrar
    (1, 'logistics_inventory', 15, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Administrator / administrar
    (1, 'logistics_location', 15, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Administrator / administrar
    (1, 'logistics_maintenance', 15, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Administrator / administrar
    (1, 'logistics_operator', 15, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Administrator / administrar
    (1, 'logistics_quotation', 15, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Administrator / administrar
    (1, 'logistics_rack', 15, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Administrator / administrar
    (1, 'logistics_rate', 15, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Administrator / administrar
    (1, 'logistics_receivable', 15, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Administrator / administrar
    (1, 'logistics_service_request', 15, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Administrator / administrar
    (1, 'logistics_shipment', 15, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Administrator / administrar
    (1, 'logistics_trailer', 15, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Administrator / administrar
    (1, 'logistics_trip', 15, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Administrator / administrar
    (1, 'logistics_unit', 15, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Administrator / administrar
    (1, 'logistics_warehouse', 15, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Administrator / administrar
    (1, 'incident', 15, 'sidebar', 'Operaciones', 'operations', 'Incidencias', 350, 'operaciones'),   -- Administrator / administrar
    (1, 'incident_detail', 15, 'sidebar', 'Operaciones', 'operations', 'Detalle de incidencias', 360, 'operaciones'),   -- Administrator / administrar
    (1, 'incident_type', 15, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Administrator / administrar
    (1, 'nm_incident_product', 15, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Administrator / administrar
    (1, 'nm_template_task', 15, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Administrator / administrar
    (1, 'proyect', 15, 'sidebar', 'Operaciones', 'operations', 'Proyectos', 310, 'operaciones'),   -- Administrator / administrar
    (1, 'task', 15, 'sidebar', 'Operaciones', 'operations', 'Tareas', 320, 'operaciones'),   -- Administrator / administrar
    (1, 'task_note', 15, 'sidebar', 'Operaciones', 'operations', 'Notas de tarea', 330, 'operaciones'),   -- Administrator / administrar
    (1, 'task_type', 15, 'sidebar', 'Operaciones', 'operations', 'Tipos de tarea', 340, 'operaciones'),   -- Administrator / administrar
    (1, 'template', 15, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Administrator / administrar
    (1, 'payroll_concept', 15, 'sidebar', 'Recursos humanos', 'hr', 'Conceptos', 720, 'rh'),   -- Administrator / administrar
    (1, 'payroll_detail', 15, 'sidebar', 'Recursos humanos', 'hr', 'Detalle', 740, 'rh'),   -- Administrator / administrar
    (1, 'payroll_movement', 15, 'sidebar', 'Recursos humanos', 'hr', 'Movimientos', 730, 'rh'),   -- Administrator / administrar
    (1, 'payroll_period', 15, 'sidebar', 'Recursos humanos', 'hr', 'Periodos de nomina', 710, 'rh'),   -- Administrator / administrar
    (1, 'entity_permission', 15, 'hidden', NULL, NULL, NULL, 990, 'seguridad'),   -- Administrator / administrar
    (1, 'field', 15, 'hidden', NULL, NULL, NULL, 990, 'seguridad'),   -- Administrator / administrar
    (1, 'nm_field_permission', 15, 'hidden', NULL, NULL, NULL, 990, 'seguridad'),   -- Administrator / administrar
    (1, 'permission', 15, 'sidebar', 'Seguridad', 'security', 'Perfiles', 920, 'seguridad'),   -- Administrator / administrar
    (1, 'user', 15, 'sidebar', 'Seguridad', 'security', 'Usuarios', 910, 'seguridad'),   -- Administrator / administrar
    (1, 'incident_supervision', 2, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Administrator / consultar
    (1, 'inventory_adjustment', 2, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Administrator / consultar
    (1, 'kronos_device', 2, 'settings', NULL, NULL, NULL, 790, 'rh'),   -- Administrator / consultar
    (1, 'pos_admin', 15, 'sidebar', 'Punto de venta', 'pos', 'Admin del punto de venta', 640, 'pos'),   -- Administrator / administrar
    (1, 'pos_terminal', 7, 'sidebar', 'Punto de venta', 'pos', 'Caja del punto de venta', 640, 'pos'),   -- Administrator / capturar
    (1, 'project_authorization', 2, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Administrator / consultar
    (1, 'project_execution', 2, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Administrator / consultar
    (1, 'restaurant_admin', 15, 'sidebar', 'Restaurante', 'restaurant', 'Admin del restaurante', 590, 'restaurante'),   -- Administrator / administrar
    (1, 'restaurant_cashier', 7, 'sidebar', 'Restaurante', 'restaurant', 'Caja', 590, 'restaurante'),   -- Administrator / capturar
    (1, 'restaurant_kitchen', 6, 'sidebar', 'Restaurante', 'restaurant', 'Cocina', 590, 'restaurante'),   -- Administrator / editar
    (1, 'restaurant_waiter', 7, 'sidebar', 'Restaurante', 'restaurant', 'Meseros', 590, 'restaurante'),   -- Administrator / capturar
    (2, 'department', 2, 'sidebar', 'Configuracion', 'settings', 'Departamentos', 830, 'configuracion'),   -- gerente_administrativo / consultar
    (2, 'level', 2, 'sidebar', 'Configuracion', 'settings', 'Niveles', 850, 'configuracion'),   -- gerente_administrativo / consultar
    (2, 'status', 2, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- gerente_administrativo / consultar
    (2, 'subdepartment', 2, 'sidebar', 'Configuracion', 'settings', 'Subdepartamentos', 840, 'configuracion'),   -- gerente_administrativo / consultar
    (2, 'theme', 2, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- gerente_administrativo / consultar
    (2, 'appointment', 7, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- gerente_administrativo / capturar
    (2, 'customer_supplier', 7, 'sidebar', 'CRM', 'crm', 'Clientes y proveedores', 620, 'crm'),   -- gerente_administrativo / capturar
    (2, 'nm_survey_user', 7, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- gerente_administrativo / capturar
    (2, 'product_sale_config', 7, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- gerente_administrativo / capturar
    (2, 'public_api_key', 7, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- gerente_administrativo / capturar
    (2, 'survey_multiple_answer', 7, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- gerente_administrativo / capturar
    (2, 'survey_question', 7, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- gerente_administrativo / capturar
    (2, 'bank', 7, 'sidebar', 'Facturacion', 'billing', 'Bancos', 140, 'facturacion'),   -- gerente_administrativo / capturar
    (2, 'bank_account', 7, 'sidebar', 'Facturacion', 'billing', 'Cuentas bancarias', 150, 'facturacion'),   -- gerente_administrativo / capturar
    (2, 'fiscal_account', 7, 'sidebar', 'Facturacion', 'billing', 'Cuentas fiscales', 130, 'facturacion'),   -- gerente_administrativo / capturar
    (2, 'fiscal_record', 7, 'hidden', NULL, NULL, NULL, 190, 'facturacion'),   -- gerente_administrativo / capturar
    (2, 'fiscal_stamp', 7, 'hidden', NULL, NULL, NULL, 190, 'facturacion'),   -- gerente_administrativo / capturar
    (2, 'invoice', 7, 'sidebar', 'Facturacion', 'billing', 'Facturas', 110, 'facturacion'),   -- gerente_administrativo / capturar
    (2, 'invoice_material_service', 7, 'hidden', NULL, NULL, NULL, 190, 'facturacion'),   -- gerente_administrativo / capturar
    (2, 'service', 7, 'hidden', NULL, NULL, NULL, 190, 'facturacion'),   -- gerente_administrativo / capturar
    (2, 'ticket', 7, 'sidebar', 'Facturacion', 'billing', 'Tickets', 160, 'facturacion'),   -- gerente_administrativo / capturar
    (2, 'brand', 2, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- gerente_administrativo / consultar
    (2, 'inventory_status', 2, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- gerente_administrativo / consultar
    (2, 'location', 2, 'sidebar', 'Inventario', 'inventory', 'Ubicaciones', 220, 'inventario'),   -- gerente_administrativo / consultar
    (2, 'location_type', 2, 'sidebar', 'Inventario', 'inventory', 'Tipos de ubicacion', 230, 'inventario'),   -- gerente_administrativo / consultar
    (2, 'material', 2, 'sidebar', 'Inventario', 'inventory', 'Materiales', 240, 'inventario'),   -- gerente_administrativo / consultar
    (2, 'material_component', 2, 'sidebar', 'Inventario', 'inventory', 'Componentes', 260, 'inventario'),   -- gerente_administrativo / consultar
    (2, 'movement', 2, 'sidebar', 'Inventario', 'inventory', 'Movimientos', 250, 'inventario'),   -- gerente_administrativo / consultar
    (2, 'product', 2, 'sidebar', 'Inventario', 'inventory', 'Productos', 210, 'inventario'),   -- gerente_administrativo / consultar
    (2, 'product_family', 2, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- gerente_administrativo / consultar
    (2, 'unit', 2, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- gerente_administrativo / consultar
    (2, 'logistics_address', 2, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- gerente_administrativo / consultar
    (2, 'logistics_branch', 2, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- gerente_administrativo / consultar
    (2, 'logistics_contact', 2, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- gerente_administrativo / consultar
    (2, 'logistics_contract', 2, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- gerente_administrativo / consultar
    (2, 'logistics_evidence', 2, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- gerente_administrativo / consultar
    (2, 'logistics_file', 2, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- gerente_administrativo / consultar
    (2, 'logistics_incident', 2, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- gerente_administrativo / consultar
    (2, 'logistics_inventory', 2, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- gerente_administrativo / consultar
    (2, 'logistics_location', 2, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- gerente_administrativo / consultar
    (2, 'logistics_maintenance', 2, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- gerente_administrativo / consultar
    (2, 'logistics_operator', 2, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- gerente_administrativo / consultar
    (2, 'logistics_quotation', 2, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- gerente_administrativo / consultar
    (2, 'logistics_rack', 2, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- gerente_administrativo / consultar
    (2, 'logistics_rate', 2, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- gerente_administrativo / consultar
    (2, 'logistics_receivable', 2, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- gerente_administrativo / consultar
    (2, 'logistics_service_request', 2, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- gerente_administrativo / consultar
    (2, 'logistics_shipment', 2, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- gerente_administrativo / consultar
    (2, 'logistics_trailer', 2, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- gerente_administrativo / consultar
    (2, 'logistics_trip', 2, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- gerente_administrativo / consultar
    (2, 'logistics_unit', 2, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- gerente_administrativo / consultar
    (2, 'logistics_warehouse', 2, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- gerente_administrativo / consultar
    (2, 'incident', 6, 'sidebar', 'Operaciones', 'operations', 'Incidencias', 350, 'operaciones'),   -- gerente_administrativo / editar
    (2, 'incident_detail', 6, 'sidebar', 'Operaciones', 'operations', 'Detalle de incidencias', 360, 'operaciones'),   -- gerente_administrativo / editar
    (2, 'incident_type', 6, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- gerente_administrativo / editar
    (2, 'nm_incident_product', 6, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- gerente_administrativo / editar
    (2, 'nm_template_task', 6, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- gerente_administrativo / editar
    (2, 'proyect', 6, 'sidebar', 'Operaciones', 'operations', 'Proyectos', 310, 'operaciones'),   -- gerente_administrativo / editar
    (2, 'task', 6, 'sidebar', 'Operaciones', 'operations', 'Tareas', 320, 'operaciones'),   -- gerente_administrativo / editar
    (2, 'task_note', 6, 'sidebar', 'Operaciones', 'operations', 'Notas de tarea', 330, 'operaciones'),   -- gerente_administrativo / editar
    (2, 'task_type', 6, 'sidebar', 'Operaciones', 'operations', 'Tipos de tarea', 340, 'operaciones'),   -- gerente_administrativo / editar
    (2, 'template', 6, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- gerente_administrativo / editar
    (2, 'payroll_concept', 7, 'sidebar', 'Recursos humanos', 'hr', 'Conceptos', 720, 'rh'),   -- gerente_administrativo / capturar
    (2, 'payroll_detail', 7, 'sidebar', 'Recursos humanos', 'hr', 'Detalle', 740, 'rh'),   -- gerente_administrativo / capturar
    (2, 'payroll_movement', 7, 'sidebar', 'Recursos humanos', 'hr', 'Movimientos', 730, 'rh'),   -- gerente_administrativo / capturar
    (2, 'payroll_period', 7, 'sidebar', 'Recursos humanos', 'hr', 'Periodos de nomina', 710, 'rh'),   -- gerente_administrativo / capturar
    (2, 'incident_supervision', 2, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- gerente_administrativo / consultar
    (2, 'kronos_device', 2, 'settings', NULL, NULL, NULL, 790, 'rh'),   -- gerente_administrativo / consultar
    (3, 'department', 2, 'sidebar', 'Configuracion', 'settings', 'Departamentos', 830, 'configuracion'),   -- vendedor / consultar
    (3, 'level', 2, 'sidebar', 'Configuracion', 'settings', 'Niveles', 850, 'configuracion'),   -- vendedor / consultar
    (3, 'status', 2, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- vendedor / consultar
    (3, 'subdepartment', 2, 'sidebar', 'Configuracion', 'settings', 'Subdepartamentos', 840, 'configuracion'),   -- vendedor / consultar
    (3, 'theme', 2, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- vendedor / consultar
    (3, 'appointment', 7, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- vendedor / capturar
    (3, 'customer_supplier', 7, 'sidebar', 'CRM', 'crm', 'Clientes y proveedores', 620, 'crm'),   -- vendedor / capturar
    (3, 'nm_survey_user', 7, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- vendedor / capturar
    (3, 'product_sale_config', 7, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- vendedor / capturar
    (3, 'public_api_key', 7, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- vendedor / capturar
    (3, 'survey_multiple_answer', 7, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- vendedor / capturar
    (3, 'survey_question', 7, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- vendedor / capturar
    (3, 'bank', 7, 'sidebar', 'Facturacion', 'billing', 'Bancos', 140, 'facturacion'),   -- vendedor / capturar
    (3, 'bank_account', 7, 'sidebar', 'Facturacion', 'billing', 'Cuentas bancarias', 150, 'facturacion'),   -- vendedor / capturar
    (3, 'fiscal_account', 7, 'sidebar', 'Facturacion', 'billing', 'Cuentas fiscales', 130, 'facturacion'),   -- vendedor / capturar
    (3, 'fiscal_record', 7, 'hidden', NULL, NULL, NULL, 190, 'facturacion'),   -- vendedor / capturar
    (3, 'fiscal_stamp', 7, 'hidden', NULL, NULL, NULL, 190, 'facturacion'),   -- vendedor / capturar
    (3, 'invoice', 7, 'sidebar', 'Facturacion', 'billing', 'Facturas', 110, 'facturacion'),   -- vendedor / capturar
    (3, 'invoice_material_service', 7, 'hidden', NULL, NULL, NULL, 190, 'facturacion'),   -- vendedor / capturar
    (3, 'service', 7, 'hidden', NULL, NULL, NULL, 190, 'facturacion'),   -- vendedor / capturar
    (3, 'ticket', 7, 'sidebar', 'Facturacion', 'billing', 'Tickets', 160, 'facturacion'),   -- vendedor / capturar
    (3, 'brand', 2, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- vendedor / consultar
    (3, 'inventory_status', 2, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- vendedor / consultar
    (3, 'location', 2, 'sidebar', 'Inventario', 'inventory', 'Ubicaciones', 220, 'inventario'),   -- vendedor / consultar
    (3, 'location_type', 2, 'sidebar', 'Inventario', 'inventory', 'Tipos de ubicacion', 230, 'inventario'),   -- vendedor / consultar
    (3, 'material', 2, 'sidebar', 'Inventario', 'inventory', 'Materiales', 240, 'inventario'),   -- vendedor / consultar
    (3, 'material_component', 2, 'sidebar', 'Inventario', 'inventory', 'Componentes', 260, 'inventario'),   -- vendedor / consultar
    (3, 'movement', 2, 'sidebar', 'Inventario', 'inventory', 'Movimientos', 250, 'inventario'),   -- vendedor / consultar
    (3, 'product', 2, 'sidebar', 'Inventario', 'inventory', 'Productos', 210, 'inventario'),   -- vendedor / consultar
    (3, 'product_family', 2, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- vendedor / consultar
    (3, 'unit', 2, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- vendedor / consultar
    (10, 'department', 2, 'sidebar', 'Configuracion', 'settings', 'Departamentos', 830, 'configuracion'),   -- Mesero / consultar
    (10, 'level', 2, 'sidebar', 'Configuracion', 'settings', 'Niveles', 850, 'configuracion'),   -- Mesero / consultar
    (10, 'status', 2, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Mesero / consultar
    (10, 'subdepartment', 2, 'sidebar', 'Configuracion', 'settings', 'Subdepartamentos', 840, 'configuracion'),   -- Mesero / consultar
    (10, 'theme', 2, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Mesero / consultar
    (10, 'restaurant_waiter', 7, 'sidebar', 'Restaurante', 'restaurant', 'Meseros', 590, 'restaurante'),   -- Mesero / capturar
    (11, 'department', 2, 'sidebar', 'Configuracion', 'settings', 'Departamentos', 830, 'configuracion'),   -- Cocina / consultar
    (11, 'level', 2, 'sidebar', 'Configuracion', 'settings', 'Niveles', 850, 'configuracion'),   -- Cocina / consultar
    (11, 'status', 2, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Cocina / consultar
    (11, 'subdepartment', 2, 'sidebar', 'Configuracion', 'settings', 'Subdepartamentos', 840, 'configuracion'),   -- Cocina / consultar
    (11, 'theme', 2, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Cocina / consultar
    (11, 'restaurant_kitchen', 6, 'sidebar', 'Restaurante', 'restaurant', 'Cocina', 590, 'restaurante'),   -- Cocina / editar
    (12, 'department', 2, 'sidebar', 'Configuracion', 'settings', 'Departamentos', 830, 'configuracion'),   -- Caja Restaurante / consultar
    (12, 'level', 2, 'sidebar', 'Configuracion', 'settings', 'Niveles', 850, 'configuracion'),   -- Caja Restaurante / consultar
    (12, 'status', 2, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Caja Restaurante / consultar
    (12, 'subdepartment', 2, 'sidebar', 'Configuracion', 'settings', 'Subdepartamentos', 840, 'configuracion'),   -- Caja Restaurante / consultar
    (12, 'theme', 2, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Caja Restaurante / consultar
    (12, 'restaurant_cashier', 7, 'sidebar', 'Restaurante', 'restaurant', 'Caja', 590, 'restaurante'),   -- Caja Restaurante / capturar
    (13, 'department', 2, 'sidebar', 'Configuracion', 'settings', 'Departamentos', 830, 'configuracion'),   -- Admin Restaurante / consultar
    (13, 'level', 2, 'sidebar', 'Configuracion', 'settings', 'Niveles', 850, 'configuracion'),   -- Admin Restaurante / consultar
    (13, 'status', 2, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Admin Restaurante / consultar
    (13, 'subdepartment', 2, 'sidebar', 'Configuracion', 'settings', 'Subdepartamentos', 840, 'configuracion'),   -- Admin Restaurante / consultar
    (13, 'theme', 2, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Admin Restaurante / consultar
    (13, 'restaurant_admin', 15, 'sidebar', 'Restaurante', 'restaurant', 'Admin del restaurante', 590, 'restaurante'),   -- Admin Restaurante / administrar
    (13, 'restaurant_cashier', 7, 'sidebar', 'Restaurante', 'restaurant', 'Caja', 590, 'restaurante'),   -- Admin Restaurante / capturar
    (13, 'restaurant_kitchen', 6, 'sidebar', 'Restaurante', 'restaurant', 'Cocina', 590, 'restaurante'),   -- Admin Restaurante / editar
    (13, 'restaurant_waiter', 7, 'sidebar', 'Restaurante', 'restaurant', 'Meseros', 590, 'restaurante'),   -- Admin Restaurante / capturar
    (14, 'department', 2, 'sidebar', 'Configuracion', 'settings', 'Departamentos', 830, 'configuracion'),   -- Jefe de taller / consultar
    (14, 'level', 2, 'sidebar', 'Configuracion', 'settings', 'Niveles', 850, 'configuracion'),   -- Jefe de taller / consultar
    (14, 'status', 2, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Jefe de taller / consultar
    (14, 'subdepartment', 2, 'sidebar', 'Configuracion', 'settings', 'Subdepartamentos', 840, 'configuracion'),   -- Jefe de taller / consultar
    (14, 'theme', 2, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Jefe de taller / consultar
    (14, 'brand', 2, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Jefe de taller / consultar
    (14, 'inventory_status', 2, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Jefe de taller / consultar
    (14, 'location', 2, 'sidebar', 'Inventario', 'inventory', 'Ubicaciones', 220, 'inventario'),   -- Jefe de taller / consultar
    (14, 'location_type', 2, 'sidebar', 'Inventario', 'inventory', 'Tipos de ubicacion', 230, 'inventario'),   -- Jefe de taller / consultar
    (14, 'material', 2, 'sidebar', 'Inventario', 'inventory', 'Materiales', 240, 'inventario'),   -- Jefe de taller / consultar
    (14, 'material_component', 2, 'sidebar', 'Inventario', 'inventory', 'Componentes', 260, 'inventario'),   -- Jefe de taller / consultar
    (14, 'movement', 2, 'sidebar', 'Inventario', 'inventory', 'Movimientos', 250, 'inventario'),   -- Jefe de taller / consultar
    (14, 'product', 2, 'sidebar', 'Inventario', 'inventory', 'Productos', 210, 'inventario'),   -- Jefe de taller / consultar
    (14, 'product_family', 2, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Jefe de taller / consultar
    (14, 'unit', 2, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Jefe de taller / consultar
    (14, 'incident', 7, 'sidebar', 'Operaciones', 'operations', 'Incidencias', 350, 'operaciones'),   -- Jefe de taller / capturar
    (14, 'incident_detail', 7, 'sidebar', 'Operaciones', 'operations', 'Detalle de incidencias', 360, 'operaciones'),   -- Jefe de taller / capturar
    (14, 'incident_type', 7, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Jefe de taller / capturar
    (14, 'nm_incident_product', 7, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Jefe de taller / capturar
    (14, 'nm_template_task', 7, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Jefe de taller / capturar
    (14, 'proyect', 7, 'sidebar', 'Operaciones', 'operations', 'Proyectos', 310, 'operaciones'),   -- Jefe de taller / capturar
    (14, 'task', 7, 'sidebar', 'Operaciones', 'operations', 'Tareas', 320, 'operaciones'),   -- Jefe de taller / capturar
    (14, 'task_note', 7, 'sidebar', 'Operaciones', 'operations', 'Notas de tarea', 330, 'operaciones'),   -- Jefe de taller / capturar
    (14, 'task_type', 7, 'sidebar', 'Operaciones', 'operations', 'Tipos de tarea', 340, 'operaciones'),   -- Jefe de taller / capturar
    (14, 'template', 7, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Jefe de taller / capturar
    (14, 'incident_supervision', 2, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Jefe de taller / consultar
    (14, 'project_execution', 2, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Jefe de taller / consultar
    (15, 'department', 2, 'sidebar', 'Configuracion', 'settings', 'Departamentos', 830, 'configuracion'),   -- Supervisor / consultar
    (15, 'level', 2, 'sidebar', 'Configuracion', 'settings', 'Niveles', 850, 'configuracion'),   -- Supervisor / consultar
    (15, 'status', 2, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Supervisor / consultar
    (15, 'subdepartment', 2, 'sidebar', 'Configuracion', 'settings', 'Subdepartamentos', 840, 'configuracion'),   -- Supervisor / consultar
    (15, 'theme', 2, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Supervisor / consultar
    (15, 'brand', 2, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Supervisor / consultar
    (15, 'inventory_status', 2, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Supervisor / consultar
    (15, 'location', 2, 'sidebar', 'Inventario', 'inventory', 'Ubicaciones', 220, 'inventario'),   -- Supervisor / consultar
    (15, 'location_type', 2, 'sidebar', 'Inventario', 'inventory', 'Tipos de ubicacion', 230, 'inventario'),   -- Supervisor / consultar
    (15, 'material', 2, 'sidebar', 'Inventario', 'inventory', 'Materiales', 240, 'inventario'),   -- Supervisor / consultar
    (15, 'material_component', 2, 'sidebar', 'Inventario', 'inventory', 'Componentes', 260, 'inventario'),   -- Supervisor / consultar
    (15, 'movement', 2, 'sidebar', 'Inventario', 'inventory', 'Movimientos', 250, 'inventario'),   -- Supervisor / consultar
    (15, 'product', 2, 'sidebar', 'Inventario', 'inventory', 'Productos', 210, 'inventario'),   -- Supervisor / consultar
    (15, 'product_family', 2, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Supervisor / consultar
    (15, 'unit', 2, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Supervisor / consultar
    (15, 'incident', 7, 'sidebar', 'Operaciones', 'operations', 'Incidencias', 350, 'operaciones'),   -- Supervisor / capturar
    (15, 'incident_detail', 7, 'sidebar', 'Operaciones', 'operations', 'Detalle de incidencias', 360, 'operaciones'),   -- Supervisor / capturar
    (15, 'incident_type', 7, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Supervisor / capturar
    (15, 'nm_incident_product', 7, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Supervisor / capturar
    (15, 'nm_template_task', 7, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Supervisor / capturar
    (15, 'proyect', 7, 'sidebar', 'Operaciones', 'operations', 'Proyectos', 310, 'operaciones'),   -- Supervisor / capturar
    (15, 'task', 7, 'sidebar', 'Operaciones', 'operations', 'Tareas', 320, 'operaciones'),   -- Supervisor / capturar
    (15, 'task_note', 7, 'sidebar', 'Operaciones', 'operations', 'Notas de tarea', 330, 'operaciones'),   -- Supervisor / capturar
    (15, 'task_type', 7, 'sidebar', 'Operaciones', 'operations', 'Tipos de tarea', 340, 'operaciones'),   -- Supervisor / capturar
    (15, 'template', 7, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Supervisor / capturar
    (15, 'incident_supervision', 2, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Supervisor / consultar
    (16, 'department', 2, 'sidebar', 'Configuracion', 'settings', 'Departamentos', 830, 'configuracion'),   -- Gerente / consultar
    (16, 'level', 2, 'sidebar', 'Configuracion', 'settings', 'Niveles', 850, 'configuracion'),   -- Gerente / consultar
    (16, 'status', 2, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Gerente / consultar
    (16, 'subdepartment', 2, 'sidebar', 'Configuracion', 'settings', 'Subdepartamentos', 840, 'configuracion'),   -- Gerente / consultar
    (16, 'theme', 2, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Gerente / consultar
    (16, 'appointment', 7, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- Gerente / capturar
    (16, 'customer_supplier', 7, 'sidebar', 'CRM', 'crm', 'Clientes y proveedores', 620, 'crm'),   -- Gerente / capturar
    (16, 'nm_survey_user', 7, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- Gerente / capturar
    (16, 'product_sale_config', 7, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- Gerente / capturar
    (16, 'public_api_key', 7, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- Gerente / capturar
    (16, 'survey_multiple_answer', 7, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- Gerente / capturar
    (16, 'survey_question', 7, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- Gerente / capturar
    (16, 'bank', 7, 'sidebar', 'Facturacion', 'billing', 'Bancos', 140, 'facturacion'),   -- Gerente / capturar
    (16, 'bank_account', 7, 'sidebar', 'Facturacion', 'billing', 'Cuentas bancarias', 150, 'facturacion'),   -- Gerente / capturar
    (16, 'fiscal_account', 7, 'sidebar', 'Facturacion', 'billing', 'Cuentas fiscales', 130, 'facturacion'),   -- Gerente / capturar
    (16, 'fiscal_record', 7, 'hidden', NULL, NULL, NULL, 190, 'facturacion'),   -- Gerente / capturar
    (16, 'fiscal_stamp', 7, 'hidden', NULL, NULL, NULL, 190, 'facturacion'),   -- Gerente / capturar
    (16, 'invoice', 7, 'sidebar', 'Facturacion', 'billing', 'Facturas', 110, 'facturacion'),   -- Gerente / capturar
    (16, 'invoice_material_service', 7, 'hidden', NULL, NULL, NULL, 190, 'facturacion'),   -- Gerente / capturar
    (16, 'service', 7, 'hidden', NULL, NULL, NULL, 190, 'facturacion'),   -- Gerente / capturar
    (16, 'ticket', 7, 'sidebar', 'Facturacion', 'billing', 'Tickets', 160, 'facturacion'),   -- Gerente / capturar
    (16, 'brand', 2, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Gerente / consultar
    (16, 'inventory_status', 2, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Gerente / consultar
    (16, 'location', 2, 'sidebar', 'Inventario', 'inventory', 'Ubicaciones', 220, 'inventario'),   -- Gerente / consultar
    (16, 'location_type', 2, 'sidebar', 'Inventario', 'inventory', 'Tipos de ubicacion', 230, 'inventario'),   -- Gerente / consultar
    (16, 'material', 2, 'sidebar', 'Inventario', 'inventory', 'Materiales', 240, 'inventario'),   -- Gerente / consultar
    (16, 'material_component', 2, 'sidebar', 'Inventario', 'inventory', 'Componentes', 260, 'inventario'),   -- Gerente / consultar
    (16, 'movement', 2, 'sidebar', 'Inventario', 'inventory', 'Movimientos', 250, 'inventario'),   -- Gerente / consultar
    (16, 'product', 2, 'sidebar', 'Inventario', 'inventory', 'Productos', 210, 'inventario'),   -- Gerente / consultar
    (16, 'product_family', 2, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Gerente / consultar
    (16, 'unit', 2, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Gerente / consultar
    (16, 'logistics_address', 2, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Gerente / consultar
    (16, 'logistics_branch', 2, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Gerente / consultar
    (16, 'logistics_contact', 2, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Gerente / consultar
    (16, 'logistics_contract', 2, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Gerente / consultar
    (16, 'logistics_evidence', 2, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Gerente / consultar
    (16, 'logistics_file', 2, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Gerente / consultar
    (16, 'logistics_incident', 2, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Gerente / consultar
    (16, 'logistics_inventory', 2, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Gerente / consultar
    (16, 'logistics_location', 2, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Gerente / consultar
    (16, 'logistics_maintenance', 2, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Gerente / consultar
    (16, 'logistics_operator', 2, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Gerente / consultar
    (16, 'logistics_quotation', 2, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Gerente / consultar
    (16, 'logistics_rack', 2, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Gerente / consultar
    (16, 'logistics_rate', 2, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Gerente / consultar
    (16, 'logistics_receivable', 2, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Gerente / consultar
    (16, 'logistics_service_request', 2, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Gerente / consultar
    (16, 'logistics_shipment', 2, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Gerente / consultar
    (16, 'logistics_trailer', 2, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Gerente / consultar
    (16, 'logistics_trip', 2, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Gerente / consultar
    (16, 'logistics_unit', 2, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Gerente / consultar
    (16, 'logistics_warehouse', 2, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Gerente / consultar
    (16, 'incident', 6, 'sidebar', 'Operaciones', 'operations', 'Incidencias', 350, 'operaciones'),   -- Gerente / editar
    (16, 'incident_detail', 6, 'sidebar', 'Operaciones', 'operations', 'Detalle de incidencias', 360, 'operaciones'),   -- Gerente / editar
    (16, 'incident_type', 6, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Gerente / editar
    (16, 'nm_incident_product', 6, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Gerente / editar
    (16, 'nm_template_task', 6, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Gerente / editar
    (16, 'proyect', 6, 'sidebar', 'Operaciones', 'operations', 'Proyectos', 310, 'operaciones'),   -- Gerente / editar
    (16, 'task', 6, 'sidebar', 'Operaciones', 'operations', 'Tareas', 320, 'operaciones'),   -- Gerente / editar
    (16, 'task_note', 6, 'sidebar', 'Operaciones', 'operations', 'Notas de tarea', 330, 'operaciones'),   -- Gerente / editar
    (16, 'task_type', 6, 'sidebar', 'Operaciones', 'operations', 'Tipos de tarea', 340, 'operaciones'),   -- Gerente / editar
    (16, 'template', 6, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Gerente / editar
    (16, 'payroll_concept', 2, 'sidebar', 'Recursos humanos', 'hr', 'Conceptos', 720, 'rh'),   -- Gerente / consultar
    (16, 'payroll_detail', 2, 'sidebar', 'Recursos humanos', 'hr', 'Detalle', 740, 'rh'),   -- Gerente / consultar
    (16, 'payroll_movement', 2, 'sidebar', 'Recursos humanos', 'hr', 'Movimientos', 730, 'rh'),   -- Gerente / consultar
    (16, 'payroll_period', 2, 'sidebar', 'Recursos humanos', 'hr', 'Periodos de nomina', 710, 'rh'),   -- Gerente / consultar
    (16, 'incident_supervision', 2, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Gerente / consultar
    (16, 'project_authorization', 2, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Gerente / consultar
    (17, 'department', 2, 'sidebar', 'Configuracion', 'settings', 'Departamentos', 830, 'configuracion'),   -- Almacenista / consultar
    (17, 'level', 2, 'sidebar', 'Configuracion', 'settings', 'Niveles', 850, 'configuracion'),   -- Almacenista / consultar
    (17, 'status', 2, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Almacenista / consultar
    (17, 'subdepartment', 2, 'sidebar', 'Configuracion', 'settings', 'Subdepartamentos', 840, 'configuracion'),   -- Almacenista / consultar
    (17, 'theme', 2, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Almacenista / consultar
    (17, 'brand', 7, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Almacenista / capturar
    (17, 'inventory_status', 7, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Almacenista / capturar
    (17, 'location', 7, 'sidebar', 'Inventario', 'inventory', 'Ubicaciones', 220, 'inventario'),   -- Almacenista / capturar
    (17, 'location_type', 7, 'sidebar', 'Inventario', 'inventory', 'Tipos de ubicacion', 230, 'inventario'),   -- Almacenista / capturar
    (17, 'material', 7, 'sidebar', 'Inventario', 'inventory', 'Materiales', 240, 'inventario'),   -- Almacenista / capturar
    (17, 'material_component', 7, 'sidebar', 'Inventario', 'inventory', 'Componentes', 260, 'inventario'),   -- Almacenista / capturar
    (17, 'movement', 7, 'sidebar', 'Inventario', 'inventory', 'Movimientos', 250, 'inventario'),   -- Almacenista / capturar
    (17, 'product', 7, 'sidebar', 'Inventario', 'inventory', 'Productos', 210, 'inventario'),   -- Almacenista / capturar
    (17, 'product_family', 7, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Almacenista / capturar
    (17, 'unit', 7, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Almacenista / capturar
    (18, 'department', 2, 'sidebar', 'Configuracion', 'settings', 'Departamentos', 830, 'configuracion'),   -- Jefe de almacen / consultar
    (18, 'level', 2, 'sidebar', 'Configuracion', 'settings', 'Niveles', 850, 'configuracion'),   -- Jefe de almacen / consultar
    (18, 'status', 2, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Jefe de almacen / consultar
    (18, 'subdepartment', 2, 'sidebar', 'Configuracion', 'settings', 'Subdepartamentos', 840, 'configuracion'),   -- Jefe de almacen / consultar
    (18, 'theme', 2, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Jefe de almacen / consultar
    (18, 'brand', 15, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Jefe de almacen / administrar
    (18, 'inventory_status', 15, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Jefe de almacen / administrar
    (18, 'location', 15, 'sidebar', 'Inventario', 'inventory', 'Ubicaciones', 220, 'inventario'),   -- Jefe de almacen / administrar
    (18, 'location_type', 15, 'sidebar', 'Inventario', 'inventory', 'Tipos de ubicacion', 230, 'inventario'),   -- Jefe de almacen / administrar
    (18, 'material', 15, 'sidebar', 'Inventario', 'inventory', 'Materiales', 240, 'inventario'),   -- Jefe de almacen / administrar
    (18, 'material_component', 15, 'sidebar', 'Inventario', 'inventory', 'Componentes', 260, 'inventario'),   -- Jefe de almacen / administrar
    (18, 'movement', 15, 'sidebar', 'Inventario', 'inventory', 'Movimientos', 250, 'inventario'),   -- Jefe de almacen / administrar
    (18, 'product', 15, 'sidebar', 'Inventario', 'inventory', 'Productos', 210, 'inventario'),   -- Jefe de almacen / administrar
    (18, 'product_family', 15, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Jefe de almacen / administrar
    (18, 'unit', 15, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Jefe de almacen / administrar
    (18, 'logistics_address', 7, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Jefe de almacen / capturar
    (18, 'logistics_branch', 7, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Jefe de almacen / capturar
    (18, 'logistics_contact', 7, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Jefe de almacen / capturar
    (18, 'logistics_contract', 7, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Jefe de almacen / capturar
    (18, 'logistics_evidence', 7, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Jefe de almacen / capturar
    (18, 'logistics_file', 7, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Jefe de almacen / capturar
    (18, 'logistics_incident', 7, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Jefe de almacen / capturar
    (18, 'logistics_inventory', 7, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Jefe de almacen / capturar
    (18, 'logistics_location', 7, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Jefe de almacen / capturar
    (18, 'logistics_maintenance', 7, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Jefe de almacen / capturar
    (18, 'logistics_operator', 7, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Jefe de almacen / capturar
    (18, 'logistics_quotation', 7, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Jefe de almacen / capturar
    (18, 'logistics_rack', 7, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Jefe de almacen / capturar
    (18, 'logistics_rate', 7, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Jefe de almacen / capturar
    (18, 'logistics_receivable', 7, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Jefe de almacen / capturar
    (18, 'logistics_service_request', 7, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Jefe de almacen / capturar
    (18, 'logistics_shipment', 7, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Jefe de almacen / capturar
    (18, 'logistics_trailer', 7, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Jefe de almacen / capturar
    (18, 'logistics_trip', 7, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Jefe de almacen / capturar
    (18, 'logistics_unit', 7, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Jefe de almacen / capturar
    (18, 'logistics_warehouse', 7, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Jefe de almacen / capturar
    (18, 'inventory_adjustment', 2, 'hidden', NULL, NULL, NULL, 290, 'inventario')   -- Jefe de almacen / consultar
) AS v (id_permission, entity_name, control_type, menu_location,
        menu_group, menu_group_icon, menu_label, menu_order, modulo_licencia)
WHERE EXISTS (SELECT 1 FROM permission p WHERE p.id_permission = v.id_permission)
  AND (
    v.modulo_licencia IN ('configuracion', 'seguridad')
    OR :'licensed_modules' = ''
    OR v.modulo_licencia = ANY(string_to_array(:'licensed_modules', ','))
  )
-- La restriccion unica es por (perfil, entidad) sin importar la baja logica, asi
-- que se reactiva la fila en lugar de insertar una segunda.
ON CONFLICT (id_permission, entity_name) DO UPDATE
   SET control_type = EXCLUDED.control_type,
       menu_location = EXCLUDED.menu_location,
       menu_group = EXCLUDED.menu_group,
       menu_group_icon = EXCLUDED.menu_group_icon,
       menu_label = EXCLUDED.menu_label,
       menu_order = EXCLUDED.menu_order,
       deletion_date = NULL,
       last_update_date = now();

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

INSERT INTO nm_field_permission (id_field, id_permission, control_type, created_by)
-- entity_permission.control_type es `text` en la base real (no coincide con
-- el `SmallInteger` que declara el modelo -- deuda aparte, no de esta
-- migracion); sin el cast, LEAST(text, integer) no resuelve tipo comun.
SELECT f.id_field, ep.id_permission, LEAST(ep.control_type::integer, 15)::text, 1
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

COMMIT;
