-- Sembrado de permisos por entidad. GENERADO por
-- backend/scripts/seed_entity_permissions.py; no editar a mano.
--
-- La revision previa a produccion encontro que 48 de las 63 entidades que el
-- backend protege no tenian ninguna fila aqui, y que ningun usuario real de la
-- base es superusuario: is_superuser solo lo da la cuenta de arranque. En la
-- practica ningun usuario real podia facturar, ver un cliente, registrar un
-- movimiento ni administrar usuarios; el front bloquea cada pantalla contra
-- esta misma tabla, asi que quedaban en blanco. Solo se habia usado el sistema
-- con la cuenta de arranque, que salta todas las comprobaciones, y por eso no
-- se noto.
--
-- Entidades cubiertas: 72. Filas generadas: 301.
-- Clasificadas pero no protegidas por ninguna ruta: ninguna.
--
-- ON CONFLICT DO NOTHING es deliberado: las filas que ya existen se dejaron
-- con valores pensados uno por uno (el almacenista mueve ubicaciones pero no
-- las da de alta, el gerente ve proyectos pero no los crea). Este sembrado
-- llena huecos; no debe pisar decisiones anteriores.

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

INSERT INTO entity_permission (
    id_permission, entity_name, scope_create, scope_read, scope_update, scope_delete, menu_location,
    menu_group, menu_group_icon, menu_label, menu_order, created_by
)
SELECT v.id_permission, v.entity_name, v.scope_create, v.scope_read, v.scope_update, v.scope_delete, v.menu_location,
       v.menu_group, v.menu_group_icon, v.menu_label, v.menu_order, 1
FROM (VALUES
    (1, 'brand', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 900),   -- Administrator / catalogos
    (1, 'department', 4, 4, 4, 4, 'sidebar', 'Configuracion', 'settings', 'Departamentos', 420),   -- Administrator / catalogos
    (1, 'incident_type', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 900),   -- Administrator / catalogos
    (1, 'inventory_status', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 900),   -- Administrator / catalogos
    (1, 'level', 4, 4, 4, 4, 'sidebar', 'Configuracion', 'settings', 'Niveles', 440),   -- Administrator / catalogos
    (1, 'location_type', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 900),   -- Administrator / catalogos
    (1, 'product_family', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 900),   -- Administrator / catalogos
    (1, 'service', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 900),   -- Administrator / catalogos
    (1, 'status', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 900),   -- Administrator / catalogos
    (1, 'subdepartment', 4, 4, 4, 4, 'sidebar', 'Configuracion', 'settings', 'Subdepartamentos', 430),   -- Administrator / catalogos
    (1, 'task_type', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 900),   -- Administrator / catalogos
    (1, 'theme', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 900),   -- Administrator / catalogos
    (1, 'unit', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 900),   -- Administrator / catalogos
    (1, 'customer_supplier', 4, 4, 4, 4, 'sidebar', 'Facturacion', 'billing', 'Clientes y proveedores', 210),   -- Administrator / comercial
    (1, 'product_sale_config', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 900),   -- Administrator / comercial
    (1, 'ticket', 4, 4, 4, 4, 'sidebar', 'Facturacion', 'billing', 'Tickets', 250),   -- Administrator / comercial
    (1, 'nm_survey_user', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 900),   -- Administrator / encuestas
    (1, 'survey_multiple_answer', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 900),   -- Administrator / encuestas
    (1, 'survey_question', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 900),   -- Administrator / encuestas
    (1, 'bank', 4, 4, 4, 4, 'sidebar', 'Facturacion', 'billing', 'Bancos', 230),   -- Administrator / facturacion
    (1, 'bank_account', 4, 4, 4, 4, 'sidebar', 'Facturacion', 'billing', 'Cuentas bancarias', 240),   -- Administrator / facturacion
    (1, 'fiscal_account', 4, 4, 4, 4, 'sidebar', 'Facturacion', 'billing', 'Cuentas fiscales', 220),   -- Administrator / facturacion
    (1, 'fiscal_record', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 900),   -- Administrator / facturacion
    (1, 'fiscal_stamp', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 900),   -- Administrator / facturacion
    (1, 'invoice', 4, 4, 4, 4, 'sidebar', 'Facturacion', 'billing', 'Facturas', 200),   -- Administrator / facturacion
    (1, 'invoice_material_service', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 900),   -- Administrator / facturacion
    (1, 'location', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 900),   -- Administrator / inventario
    (1, 'material', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 900),   -- Administrator / inventario
    (1, 'material_component', 4, 4, 4, 4, 'sidebar', 'Inventario', 'inventory', 'Componentes', 190),   -- Administrator / inventario
    (1, 'movement', 4, 4, 4, 4, 'sidebar', 'Inventario', 'inventory', 'Movimientos', 180),   -- Administrator / inventario
    (1, 'product', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 900),   -- Administrator / inventario
    (1, 'logistics_address', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 900),   -- Administrator / logistica
    (1, 'logistics_branch', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 900),   -- Administrator / logistica
    (1, 'logistics_contact', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 900),   -- Administrator / logistica
    (1, 'logistics_contract', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 900),   -- Administrator / logistica
    (1, 'logistics_evidence', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 900),   -- Administrator / logistica
    (1, 'logistics_file', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 900),   -- Administrator / logistica
    (1, 'logistics_incident', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 900),   -- Administrator / logistica
    (1, 'logistics_inventory', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 900),   -- Administrator / logistica
    (1, 'logistics_location', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 900),   -- Administrator / logistica
    (1, 'logistics_maintenance', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 900),   -- Administrator / logistica
    (1, 'logistics_operator', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 900),   -- Administrator / logistica
    (1, 'logistics_quotation', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 900),   -- Administrator / logistica
    (1, 'logistics_rack', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 900),   -- Administrator / logistica
    (1, 'logistics_rate', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 900),   -- Administrator / logistica
    (1, 'logistics_receivable', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 900),   -- Administrator / logistica
    (1, 'logistics_service_request', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 900),   -- Administrator / logistica
    (1, 'logistics_shipment', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 900),   -- Administrator / logistica
    (1, 'logistics_trailer', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 900),   -- Administrator / logistica
    (1, 'logistics_trip', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 900),   -- Administrator / logistica
    (1, 'logistics_unit', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 900),   -- Administrator / logistica
    (1, 'logistics_warehouse', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 900),   -- Administrator / logistica
    (1, 'kronos_device', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 900),   -- Administrator / nomina
    (1, 'payroll_concept', 4, 4, 4, 4, 'sidebar', 'Recursos humanos', 'hr', 'Conceptos', 310),   -- Administrator / nomina
    (1, 'payroll_detail', 4, 4, 4, 4, 'sidebar', 'Recursos humanos', 'hr', 'Detalle', 330),   -- Administrator / nomina
    (1, 'payroll_movement', 4, 4, 4, 4, 'sidebar', 'Recursos humanos', 'hr', 'Movimientos', 320),   -- Administrator / nomina
    (1, 'payroll_period', 4, 4, 4, 4, 'sidebar', 'Recursos humanos', 'hr', 'Periodos de nomina', 300),   -- Administrator / nomina
    (1, 'appointment', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 900),   -- Administrator / operaciones
    (1, 'incident', 4, 4, 4, 4, 'sidebar', 'Operaciones', 'operations', 'Incidencias', 120),   -- Administrator / operaciones
    (1, 'incident_detail', 4, 4, 4, 4, 'sidebar', 'Operaciones', 'operations', 'Detalle de incidencias', 130),   -- Administrator / operaciones
    (1, 'nm_incident_product', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 900),   -- Administrator / operaciones
    (1, 'nm_template_task', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 900),   -- Administrator / operaciones
    (1, 'proyect', 4, 4, 4, 4, 'sidebar', 'Operaciones', 'operations', 'Proyectos', 80),   -- Administrator / operaciones
    (1, 'task', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 900),   -- Administrator / operaciones
    (1, 'task_note', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 900),   -- Administrator / operaciones
    (1, 'template', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 900),   -- Administrator / operaciones
    (1, 'entity_permission', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 900),   -- Administrator / seguridad
    (1, 'field', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 900),   -- Administrator / seguridad
    (1, 'nm_field_permission', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 900),   -- Administrator / seguridad
    (1, 'permission', 4, 4, 4, 4, 'sidebar', 'Configuracion', 'settings', 'Perfiles', 410),   -- Administrator / seguridad
    (1, 'public_api_key', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 900),   -- Administrator / seguridad
    (1, 'user', 4, 4, 4, 4, 'sidebar', 'Configuracion', 'settings', 'Usuarios', 400),   -- Administrator / seguridad
    (2, 'brand', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- gerente_administrativo / catalogos
    (2, 'department', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Departamentos', 420),   -- gerente_administrativo / catalogos
    (2, 'incident_type', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- gerente_administrativo / catalogos
    (2, 'inventory_status', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- gerente_administrativo / catalogos
    (2, 'level', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Niveles', 440),   -- gerente_administrativo / catalogos
    (2, 'location_type', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- gerente_administrativo / catalogos
    (2, 'product_family', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- gerente_administrativo / catalogos
    (2, 'service', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- gerente_administrativo / catalogos
    (2, 'status', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- gerente_administrativo / catalogos
    (2, 'subdepartment', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Subdepartamentos', 430),   -- gerente_administrativo / catalogos
    (2, 'task_type', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- gerente_administrativo / catalogos
    (2, 'theme', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- gerente_administrativo / catalogos
    (2, 'unit', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- gerente_administrativo / catalogos
    (2, 'customer_supplier', 4, 4, 4, 0, 'sidebar', 'Facturacion', 'billing', 'Clientes y proveedores', 210),   -- gerente_administrativo / comercial
    (2, 'product_sale_config', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 900),   -- gerente_administrativo / comercial
    (2, 'ticket', 4, 4, 4, 0, 'sidebar', 'Facturacion', 'billing', 'Tickets', 250),   -- gerente_administrativo / comercial
    (2, 'nm_survey_user', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- gerente_administrativo / encuestas
    (2, 'survey_multiple_answer', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- gerente_administrativo / encuestas
    (2, 'survey_question', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- gerente_administrativo / encuestas
    (2, 'bank', 4, 4, 4, 0, 'sidebar', 'Facturacion', 'billing', 'Bancos', 230),   -- gerente_administrativo / facturacion
    (2, 'bank_account', 4, 4, 4, 0, 'sidebar', 'Facturacion', 'billing', 'Cuentas bancarias', 240),   -- gerente_administrativo / facturacion
    (2, 'fiscal_account', 4, 4, 4, 0, 'sidebar', 'Facturacion', 'billing', 'Cuentas fiscales', 220),   -- gerente_administrativo / facturacion
    (2, 'fiscal_record', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 900),   -- gerente_administrativo / facturacion
    (2, 'fiscal_stamp', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 900),   -- gerente_administrativo / facturacion
    (2, 'invoice', 4, 4, 4, 0, 'sidebar', 'Facturacion', 'billing', 'Facturas', 200),   -- gerente_administrativo / facturacion
    (2, 'invoice_material_service', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 900),   -- gerente_administrativo / facturacion
    (2, 'location', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- gerente_administrativo / inventario
    (2, 'material', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- gerente_administrativo / inventario
    (2, 'material_component', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Componentes', 190),   -- gerente_administrativo / inventario
    (2, 'movement', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Movimientos', 180),   -- gerente_administrativo / inventario
    (2, 'product', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- gerente_administrativo / inventario
    (2, 'kronos_device', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 900),   -- gerente_administrativo / nomina
    (2, 'payroll_concept', 4, 4, 4, 0, 'sidebar', 'Recursos humanos', 'hr', 'Conceptos', 310),   -- gerente_administrativo / nomina
    (2, 'payroll_detail', 4, 4, 4, 0, 'sidebar', 'Recursos humanos', 'hr', 'Detalle', 330),   -- gerente_administrativo / nomina
    (2, 'payroll_movement', 4, 4, 4, 0, 'sidebar', 'Recursos humanos', 'hr', 'Movimientos', 320),   -- gerente_administrativo / nomina
    (2, 'payroll_period', 4, 4, 4, 0, 'sidebar', 'Recursos humanos', 'hr', 'Periodos de nomina', 300),   -- gerente_administrativo / nomina
    (2, 'appointment', 0, 4, 4, 0, 'hidden', NULL, NULL, NULL, 900),   -- gerente_administrativo / operaciones
    (2, 'incident', 0, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Incidencias', 120),   -- gerente_administrativo / operaciones
    (2, 'incident_detail', 0, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Detalle de incidencias', 130),   -- gerente_administrativo / operaciones
    (2, 'nm_incident_product', 0, 4, 4, 0, 'hidden', NULL, NULL, NULL, 900),   -- gerente_administrativo / operaciones
    (2, 'nm_template_task', 0, 4, 4, 0, 'hidden', NULL, NULL, NULL, 900),   -- gerente_administrativo / operaciones
    (2, 'proyect', 0, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Proyectos', 80),   -- gerente_administrativo / operaciones
    (2, 'task', 0, 4, 4, 0, 'hidden', NULL, NULL, NULL, 900),   -- gerente_administrativo / operaciones
    (2, 'task_note', 0, 4, 4, 0, 'hidden', NULL, NULL, NULL, 900),   -- gerente_administrativo / operaciones
    (2, 'template', 0, 4, 4, 0, 'hidden', NULL, NULL, NULL, 900),   -- gerente_administrativo / operaciones
    (3, 'brand', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- vendedor / catalogos
    (3, 'department', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Departamentos', 420),   -- vendedor / catalogos
    (3, 'incident_type', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- vendedor / catalogos
    (3, 'inventory_status', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- vendedor / catalogos
    (3, 'level', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Niveles', 440),   -- vendedor / catalogos
    (3, 'location_type', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- vendedor / catalogos
    (3, 'product_family', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- vendedor / catalogos
    (3, 'service', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- vendedor / catalogos
    (3, 'status', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- vendedor / catalogos
    (3, 'subdepartment', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Subdepartamentos', 430),   -- vendedor / catalogos
    (3, 'task_type', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- vendedor / catalogos
    (3, 'theme', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- vendedor / catalogos
    (3, 'unit', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- vendedor / catalogos
    (3, 'customer_supplier', 4, 4, 4, 0, 'sidebar', 'Facturacion', 'billing', 'Clientes y proveedores', 210),   -- vendedor / comercial
    (3, 'product_sale_config', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 900),   -- vendedor / comercial
    (3, 'ticket', 4, 4, 4, 0, 'sidebar', 'Facturacion', 'billing', 'Tickets', 250),   -- vendedor / comercial
    (3, 'bank', 4, 4, 4, 0, 'sidebar', 'Facturacion', 'billing', 'Bancos', 230),   -- vendedor / facturacion
    (3, 'bank_account', 4, 4, 4, 0, 'sidebar', 'Facturacion', 'billing', 'Cuentas bancarias', 240),   -- vendedor / facturacion
    (3, 'fiscal_account', 4, 4, 4, 0, 'sidebar', 'Facturacion', 'billing', 'Cuentas fiscales', 220),   -- vendedor / facturacion
    (3, 'fiscal_record', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 900),   -- vendedor / facturacion
    (3, 'fiscal_stamp', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 900),   -- vendedor / facturacion
    (3, 'invoice', 4, 4, 4, 0, 'sidebar', 'Facturacion', 'billing', 'Facturas', 200),   -- vendedor / facturacion
    (3, 'invoice_material_service', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 900),   -- vendedor / facturacion
    (3, 'location', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- vendedor / inventario
    (3, 'material', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- vendedor / inventario
    (3, 'material_component', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Componentes', 190),   -- vendedor / inventario
    (3, 'movement', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Movimientos', 180),   -- vendedor / inventario
    (3, 'product', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- vendedor / inventario
    (14, 'brand', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- Jefe de taller / catalogos
    (14, 'department', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Departamentos', 420),   -- Jefe de taller / catalogos
    (14, 'incident_type', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- Jefe de taller / catalogos
    (14, 'inventory_status', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- Jefe de taller / catalogos
    (14, 'level', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Niveles', 440),   -- Jefe de taller / catalogos
    (14, 'location_type', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- Jefe de taller / catalogos
    (14, 'product_family', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- Jefe de taller / catalogos
    (14, 'service', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- Jefe de taller / catalogos
    (14, 'status', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- Jefe de taller / catalogos
    (14, 'subdepartment', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Subdepartamentos', 430),   -- Jefe de taller / catalogos
    (14, 'task_type', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- Jefe de taller / catalogos
    (14, 'theme', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- Jefe de taller / catalogos
    (14, 'unit', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- Jefe de taller / catalogos
    (14, 'location', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- Jefe de taller / inventario
    (14, 'material', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- Jefe de taller / inventario
    (14, 'material_component', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Componentes', 190),   -- Jefe de taller / inventario
    (14, 'movement', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Movimientos', 180),   -- Jefe de taller / inventario
    (14, 'product', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- Jefe de taller / inventario
    (14, 'appointment', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 900),   -- Jefe de taller / operaciones
    (14, 'incident', 4, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Incidencias', 120),   -- Jefe de taller / operaciones
    (14, 'incident_detail', 4, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Detalle de incidencias', 130),   -- Jefe de taller / operaciones
    (14, 'nm_incident_product', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 900),   -- Jefe de taller / operaciones
    (14, 'nm_template_task', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 900),   -- Jefe de taller / operaciones
    (14, 'proyect', 4, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Proyectos', 80),   -- Jefe de taller / operaciones
    (14, 'task', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 900),   -- Jefe de taller / operaciones
    (14, 'task_note', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 900),   -- Jefe de taller / operaciones
    (14, 'template', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 900),   -- Jefe de taller / operaciones
    (15, 'brand', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- Supervisor / catalogos
    (15, 'department', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Departamentos', 420),   -- Supervisor / catalogos
    (15, 'incident_type', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- Supervisor / catalogos
    (15, 'inventory_status', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- Supervisor / catalogos
    (15, 'level', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Niveles', 440),   -- Supervisor / catalogos
    (15, 'location_type', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- Supervisor / catalogos
    (15, 'product_family', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- Supervisor / catalogos
    (15, 'service', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- Supervisor / catalogos
    (15, 'status', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- Supervisor / catalogos
    (15, 'subdepartment', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Subdepartamentos', 430),   -- Supervisor / catalogos
    (15, 'task_type', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- Supervisor / catalogos
    (15, 'theme', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- Supervisor / catalogos
    (15, 'unit', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- Supervisor / catalogos
    (15, 'location', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- Supervisor / inventario
    (15, 'material', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- Supervisor / inventario
    (15, 'material_component', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Componentes', 190),   -- Supervisor / inventario
    (15, 'movement', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Movimientos', 180),   -- Supervisor / inventario
    (15, 'product', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- Supervisor / inventario
    (15, 'appointment', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 900),   -- Supervisor / operaciones
    (15, 'incident', 4, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Incidencias', 120),   -- Supervisor / operaciones
    (15, 'incident_detail', 4, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Detalle de incidencias', 130),   -- Supervisor / operaciones
    (15, 'nm_incident_product', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 900),   -- Supervisor / operaciones
    (15, 'nm_template_task', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 900),   -- Supervisor / operaciones
    (15, 'proyect', 4, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Proyectos', 80),   -- Supervisor / operaciones
    (15, 'task', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 900),   -- Supervisor / operaciones
    (15, 'task_note', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 900),   -- Supervisor / operaciones
    (15, 'template', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 900),   -- Supervisor / operaciones
    (16, 'brand', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- Gerente / catalogos
    (16, 'department', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Departamentos', 420),   -- Gerente / catalogos
    (16, 'incident_type', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- Gerente / catalogos
    (16, 'inventory_status', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- Gerente / catalogos
    (16, 'level', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Niveles', 440),   -- Gerente / catalogos
    (16, 'location_type', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- Gerente / catalogos
    (16, 'product_family', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- Gerente / catalogos
    (16, 'service', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- Gerente / catalogos
    (16, 'status', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- Gerente / catalogos
    (16, 'subdepartment', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Subdepartamentos', 430),   -- Gerente / catalogos
    (16, 'task_type', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- Gerente / catalogos
    (16, 'theme', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- Gerente / catalogos
    (16, 'unit', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- Gerente / catalogos
    (16, 'customer_supplier', 4, 4, 4, 0, 'sidebar', 'Facturacion', 'billing', 'Clientes y proveedores', 210),   -- Gerente / comercial
    (16, 'product_sale_config', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 900),   -- Gerente / comercial
    (16, 'ticket', 4, 4, 4, 0, 'sidebar', 'Facturacion', 'billing', 'Tickets', 250),   -- Gerente / comercial
    (16, 'nm_survey_user', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- Gerente / encuestas
    (16, 'survey_multiple_answer', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- Gerente / encuestas
    (16, 'survey_question', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- Gerente / encuestas
    (16, 'bank', 4, 4, 4, 0, 'sidebar', 'Facturacion', 'billing', 'Bancos', 230),   -- Gerente / facturacion
    (16, 'bank_account', 4, 4, 4, 0, 'sidebar', 'Facturacion', 'billing', 'Cuentas bancarias', 240),   -- Gerente / facturacion
    (16, 'fiscal_account', 4, 4, 4, 0, 'sidebar', 'Facturacion', 'billing', 'Cuentas fiscales', 220),   -- Gerente / facturacion
    (16, 'fiscal_record', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 900),   -- Gerente / facturacion
    (16, 'fiscal_stamp', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 900),   -- Gerente / facturacion
    (16, 'invoice', 4, 4, 4, 0, 'sidebar', 'Facturacion', 'billing', 'Facturas', 200),   -- Gerente / facturacion
    (16, 'invoice_material_service', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 900),   -- Gerente / facturacion
    (16, 'location', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- Gerente / inventario
    (16, 'material', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- Gerente / inventario
    (16, 'material_component', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Componentes', 190),   -- Gerente / inventario
    (16, 'movement', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Movimientos', 180),   -- Gerente / inventario
    (16, 'product', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- Gerente / inventario
    (16, 'kronos_device', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- Gerente / nomina
    (16, 'payroll_concept', 0, 4, 0, 0, 'sidebar', 'Recursos humanos', 'hr', 'Conceptos', 310),   -- Gerente / nomina
    (16, 'payroll_detail', 0, 4, 0, 0, 'sidebar', 'Recursos humanos', 'hr', 'Detalle', 330),   -- Gerente / nomina
    (16, 'payroll_movement', 0, 4, 0, 0, 'sidebar', 'Recursos humanos', 'hr', 'Movimientos', 320),   -- Gerente / nomina
    (16, 'payroll_period', 0, 4, 0, 0, 'sidebar', 'Recursos humanos', 'hr', 'Periodos de nomina', 300),   -- Gerente / nomina
    (16, 'appointment', 0, 4, 4, 0, 'hidden', NULL, NULL, NULL, 900),   -- Gerente / operaciones
    (16, 'incident', 0, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Incidencias', 120),   -- Gerente / operaciones
    (16, 'incident_detail', 0, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Detalle de incidencias', 130),   -- Gerente / operaciones
    (16, 'nm_incident_product', 0, 4, 4, 0, 'hidden', NULL, NULL, NULL, 900),   -- Gerente / operaciones
    (16, 'nm_template_task', 0, 4, 4, 0, 'hidden', NULL, NULL, NULL, 900),   -- Gerente / operaciones
    (16, 'proyect', 0, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Proyectos', 80),   -- Gerente / operaciones
    (16, 'task', 0, 4, 4, 0, 'hidden', NULL, NULL, NULL, 900),   -- Gerente / operaciones
    (16, 'task_note', 0, 4, 4, 0, 'hidden', NULL, NULL, NULL, 900),   -- Gerente / operaciones
    (16, 'template', 0, 4, 4, 0, 'hidden', NULL, NULL, NULL, 900),   -- Gerente / operaciones
    (17, 'brand', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- Almacenista / catalogos
    (17, 'department', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Departamentos', 420),   -- Almacenista / catalogos
    (17, 'incident_type', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- Almacenista / catalogos
    (17, 'inventory_status', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- Almacenista / catalogos
    (17, 'level', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Niveles', 440),   -- Almacenista / catalogos
    (17, 'location_type', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- Almacenista / catalogos
    (17, 'product_family', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- Almacenista / catalogos
    (17, 'service', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- Almacenista / catalogos
    (17, 'status', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- Almacenista / catalogos
    (17, 'subdepartment', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Subdepartamentos', 430),   -- Almacenista / catalogos
    (17, 'task_type', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- Almacenista / catalogos
    (17, 'theme', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- Almacenista / catalogos
    (17, 'unit', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- Almacenista / catalogos
    (17, 'location', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 900),   -- Almacenista / inventario
    (17, 'material', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 900),   -- Almacenista / inventario
    (17, 'material_component', 4, 4, 4, 0, 'sidebar', 'Inventario', 'inventory', 'Componentes', 190),   -- Almacenista / inventario
    (17, 'movement', 4, 4, 4, 0, 'sidebar', 'Inventario', 'inventory', 'Movimientos', 180),   -- Almacenista / inventario
    (17, 'product', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 900),   -- Almacenista / inventario
    (18, 'brand', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- Jefe de almacen / catalogos
    (18, 'department', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Departamentos', 420),   -- Jefe de almacen / catalogos
    (18, 'incident_type', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- Jefe de almacen / catalogos
    (18, 'inventory_status', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- Jefe de almacen / catalogos
    (18, 'level', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Niveles', 440),   -- Jefe de almacen / catalogos
    (18, 'location_type', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- Jefe de almacen / catalogos
    (18, 'product_family', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- Jefe de almacen / catalogos
    (18, 'service', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- Jefe de almacen / catalogos
    (18, 'status', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- Jefe de almacen / catalogos
    (18, 'subdepartment', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Subdepartamentos', 430),   -- Jefe de almacen / catalogos
    (18, 'task_type', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- Jefe de almacen / catalogos
    (18, 'theme', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- Jefe de almacen / catalogos
    (18, 'unit', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 900),   -- Jefe de almacen / catalogos
    (18, 'location', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 900),   -- Jefe de almacen / inventario
    (18, 'material', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 900),   -- Jefe de almacen / inventario
    (18, 'material_component', 4, 4, 4, 4, 'sidebar', 'Inventario', 'inventory', 'Componentes', 190),   -- Jefe de almacen / inventario
    (18, 'movement', 4, 4, 4, 4, 'sidebar', 'Inventario', 'inventory', 'Movimientos', 180),   -- Jefe de almacen / inventario
    (18, 'product', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 900),   -- Jefe de almacen / inventario
    (18, 'logistics_address', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 900),   -- Jefe de almacen / logistica
    (18, 'logistics_branch', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 900),   -- Jefe de almacen / logistica
    (18, 'logistics_contact', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 900),   -- Jefe de almacen / logistica
    (18, 'logistics_contract', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 900),   -- Jefe de almacen / logistica
    (18, 'logistics_evidence', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 900),   -- Jefe de almacen / logistica
    (18, 'logistics_file', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 900),   -- Jefe de almacen / logistica
    (18, 'logistics_incident', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 900),   -- Jefe de almacen / logistica
    (18, 'logistics_inventory', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 900),   -- Jefe de almacen / logistica
    (18, 'logistics_location', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 900),   -- Jefe de almacen / logistica
    (18, 'logistics_maintenance', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 900),   -- Jefe de almacen / logistica
    (18, 'logistics_operator', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 900),   -- Jefe de almacen / logistica
    (18, 'logistics_quotation', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 900),   -- Jefe de almacen / logistica
    (18, 'logistics_rack', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 900),   -- Jefe de almacen / logistica
    (18, 'logistics_rate', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 900),   -- Jefe de almacen / logistica
    (18, 'logistics_receivable', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 900),   -- Jefe de almacen / logistica
    (18, 'logistics_service_request', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 900),   -- Jefe de almacen / logistica
    (18, 'logistics_shipment', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 900),   -- Jefe de almacen / logistica
    (18, 'logistics_trailer', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 900),   -- Jefe de almacen / logistica
    (18, 'logistics_trip', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 900),   -- Jefe de almacen / logistica
    (18, 'logistics_unit', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 900),   -- Jefe de almacen / logistica
    (18, 'logistics_warehouse', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 900)   -- Jefe de almacen / logistica
) AS v (id_permission, entity_name, scope_create, scope_read, scope_update, scope_delete, menu_location,
        menu_group, menu_group_icon, menu_label, menu_order)
WHERE EXISTS (SELECT 1 FROM permission p WHERE p.id_permission = v.id_permission)
ON CONFLICT (id_permission, entity_name) DO NOTHING;

END IF;
END $$;

COMMIT;
