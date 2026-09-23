-- Permisos por modulo y accion CRUD. GENERADO por
-- backend/scripts/seed_module_permissions.py desde app/modules/registry.py.
-- No editar a mano: el registro es la fuente de verdad y cualquier cambio aqui
-- se pierde en la siguiente generacion.
--
-- ESTE ES EL UNICO ARCHIVO GENERADO DE LA MATRIZ QUE DEBE EXISTIR.
-- Al cambiar `registry.py` hay que REGENERAR este archivo:
--
--     python scripts/seed_module_permissions.py \
--         ../database/migrations/20260901000000_module_permission_matrix_licensed.sql
--
-- No agregar una copia nueva con otro timestamp. Ya paso una vez: la Fase 2
-- de facturacion agrego `20260901020000_multiemisor_capacidad.sql`, otra copia
-- completa de esta matriz, en lugar de regenerar esta. Como cada copia empieza
-- dando de baja logica TODO `entity_permission` y resiembra solo su propia
-- lista, la copia con el timestamp mas alto gana en silencio: los modulos que
-- solo estaban declarados en la otra quedaban con 0 permisos vigentes en cada
-- arranque del pod, sin ningun error en los logs.
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
-- 11 modulos, 12 roles, 12 capacidades,
-- 389 filas.
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
--   laboratorio      7 entidades
--     Administrator (administrar)
--   rh               4 entidades
--     Administrator (administrar), gerente_administrativo (capturar), Gerente (consultar)
--   configuracion    5 entidades
--     Administrator (administrar), gerente_administrativo (consultar), vendedor (consultar), Mesero (consultar), Cocina (consultar), Caja Restaurante (consultar), Admin Restaurante (consultar), Jefe de taller (consultar), Supervisor (consultar), Gerente (consultar), Almacenista (consultar), Jefe de almacen (consultar)
--   seguridad        7 entidades
--     Administrator (administrar)

BEGIN;

-- NO se marca de baja lo vigente antes de sembrar.
--
-- Lo hacia, y esa linea es la que se retira. Corria en cada reinicio del pod,
-- asi que cualquier ajuste hecho desde el gestor de roles se revertia en el
-- siguiente despliegue. Medido antes del cambio: un administrador subia el
-- permiso de un rol sobre `product` de 2 a 15, se reaplicaban las migraciones,
-- y volvia a 2.
--
-- La decision es que el gestor manda y el registro solo siembra lo que falta.
-- El registro sigue siendo la fuente de los valores POR OMISION -lo que recibe
-- un modulo nuevo o un rol nuevo- y deja de ser la fuente de la verdad sobre
-- quien puede que, que es lo que el gestor administra.
--
-- Lo que retiraba esta linea cuando cambiaba la licencia ya no hace falta: el
-- plan se comprueba en cada peticion -`require_entity_permission` y
-- `has_capability`- y filtra el menu en `my-permissions`. Un modulo fuera del
-- plan es inalcanzable aunque su fila exista, asi que no hay que borrarla para
-- retirarlo. Ver `app/modules/plan.py`.

-- Antes de sembrar: se borran las bajas que dejo el mecanismo VIEJO.
--
-- Hasta este cambio, este archivo marcaba de baja todo lo vigente en cada
-- reinicio antes de insertar. Las filas que quedaron de baja por eso no las
-- quito nadie: son residuo. Y el sembrado nuevo respeta una baja -porque desde
-- ahora significa que el administrador la quito-, asi que sin esta limpieza
-- esos permisos no volverian nunca.
--
-- Se borran fisicamente para que el INSERT de abajo las vuelva a crear con el
-- valor por omision del registro, que es el punto de partida correcto.
--
-- La fecha esta fija a proposito. Esta migracion se reaplica en cada arranque
-- del pod: sin la cota, cada despliegue borraria tambien las bajas que el
-- administrador hizo despues, o sea el problema que estamos arreglando. Antes
-- de la cota es residuo; despues, decision de alguien.
DELETE FROM entity_permission
 WHERE deletion_date IS NOT NULL
   AND deletion_date < TIMESTAMP '2026-09-02 18:00:00';

-- Guardado con un chequeo de existencia de scope_create: esta migracion es
-- anterior a 20260914110000_equipos_y_alcance_por_accion.sql, que agrega esas
-- 4 columnas y suelta control_type mas adelante en la misma pasada. Sin este
-- guardado, la primera pasada completa contra un volumen nuevo tronaria aqui
-- con "column scope_create does not exist".
--
-- `:'licensed_modules'` (sustitucion de psql) no se interpola DENTRO de un
-- bloque `DO $$ ... $$`: psql trata todo el cuerpo entre dolares como un
-- solo token opaco para su propio lexer, asi que `:'licensed_modules'`
-- viajaria literal al servidor y Postgres lo rechaza con "syntax error at
-- or near ':'". Se captura aqui, en una sentencia plana (fuera de
-- cualquier $$), en una variable de sesion que el bloque DO si puede leer.
SELECT set_config('tyakxa.licensed_modules', :'licensed_modules', false);

DO $$
DECLARE
  licensed_modules text := current_setting('tyakxa.licensed_modules', true);
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
    (1, 'department', 4, 4, 4, 4, 'sidebar', 'Configuracion', 'settings', 'Departamentos', 830, 'configuracion'),   -- Administrator / administrar
    (1, 'level', 4, 4, 4, 4, 'sidebar', 'Configuracion', 'settings', 'Niveles', 850, 'configuracion'),   -- Administrator / administrar
    (1, 'status', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Administrator / administrar
    (1, 'subdepartment', 4, 4, 4, 4, 'sidebar', 'Configuracion', 'settings', 'Subdepartamentos', 840, 'configuracion'),   -- Administrator / administrar
    (1, 'theme', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Administrator / administrar
    (1, 'appointment', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- Administrator / administrar
    (1, 'customer_supplier', 4, 4, 4, 4, 'sidebar', 'CRM', 'crm', 'Clientes y proveedores', 620, 'crm'),   -- Administrator / administrar
    (1, 'nm_survey_user', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- Administrator / administrar
    (1, 'product_sale_config', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- Administrator / administrar
    (1, 'public_api_key', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- Administrator / administrar
    (1, 'survey_multiple_answer', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- Administrator / administrar
    (1, 'survey_question', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- Administrator / administrar
    (1, 'bank', 4, 4, 4, 4, 'sidebar', 'Facturacion', 'billing', 'Bancos', 140, 'facturacion'),   -- Administrator / administrar
    (1, 'bank_account', 4, 4, 4, 4, 'sidebar', 'Facturacion', 'billing', 'Cuentas bancarias', 150, 'facturacion'),   -- Administrator / administrar
    (1, 'fiscal_account', 4, 4, 4, 4, 'sidebar', 'Facturacion', 'billing', 'Cuentas fiscales', 130, 'facturacion'),   -- Administrator / administrar
    (1, 'fiscal_record', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 190, 'facturacion'),   -- Administrator / administrar
    (1, 'fiscal_stamp', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 190, 'facturacion'),   -- Administrator / administrar
    (1, 'invoice', 4, 4, 4, 4, 'sidebar', 'Facturacion', 'billing', 'Facturas', 110, 'facturacion'),   -- Administrator / administrar
    (1, 'invoice_material_service', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 190, 'facturacion'),   -- Administrator / administrar
    (1, 'service', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 190, 'facturacion'),   -- Administrator / administrar
    (1, 'ticket', 4, 4, 4, 4, 'sidebar', 'Facturacion', 'billing', 'Tickets', 160, 'facturacion'),   -- Administrator / administrar
    (1, 'brand', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Administrator / administrar
    (1, 'inventory_status', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Administrator / administrar
    (1, 'location', 4, 4, 4, 4, 'sidebar', 'Inventario', 'inventory', 'Ubicaciones', 220, 'inventario'),   -- Administrator / administrar
    (1, 'location_type', 4, 4, 4, 4, 'sidebar', 'Inventario', 'inventory', 'Tipos de ubicacion', 230, 'inventario'),   -- Administrator / administrar
    (1, 'material', 4, 4, 4, 4, 'sidebar', 'Inventario', 'inventory', 'Materiales', 240, 'inventario'),   -- Administrator / administrar
    (1, 'material_component', 4, 4, 4, 4, 'sidebar', 'Inventario', 'inventory', 'Componentes', 260, 'inventario'),   -- Administrator / administrar
    (1, 'movement', 4, 4, 4, 4, 'sidebar', 'Inventario', 'inventory', 'Movimientos', 250, 'inventario'),   -- Administrator / administrar
    (1, 'product', 4, 4, 4, 4, 'sidebar', 'Inventario', 'inventory', 'Productos', 210, 'inventario'),   -- Administrator / administrar
    (1, 'product_family', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Administrator / administrar
    (1, 'unit', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Administrator / administrar
    (1, 'document', 4, 4, 4, 4, 'sidebar', 'Laboratorio', 'clipboard-list', 'Documentos', 660, 'laboratorio'),   -- Administrator / administrar
    (1, 'document_category', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 740, 'laboratorio'),   -- Administrator / administrar
    (1, 'document_relation', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 740, 'laboratorio'),   -- Administrator / administrar
    (1, 'document_version', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 740, 'laboratorio'),   -- Administrator / administrar
    (1, 'laboratory_equipment', 4, 4, 4, 4, 'sidebar', 'Laboratorio', 'clipboard-list', 'Equipos de laboratorio', 670, 'laboratorio'),   -- Administrator / administrar
    (1, 'laboratory_service_order', 4, 4, 4, 4, 'sidebar', 'Laboratorio', 'clipboard-list', 'Ordenes de servicio', 680, 'laboratorio'),   -- Administrator / administrar
    (1, 'laboratory_service_order_status_history', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 740, 'laboratorio'),   -- Administrator / administrar
    (1, 'logistics_address', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Administrator / administrar
    (1, 'logistics_branch', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Administrator / administrar
    (1, 'logistics_contact', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Administrator / administrar
    (1, 'logistics_contract', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Administrator / administrar
    (1, 'logistics_evidence', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Administrator / administrar
    (1, 'logistics_file', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Administrator / administrar
    (1, 'logistics_incident', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Administrator / administrar
    (1, 'logistics_inventory', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Administrator / administrar
    (1, 'logistics_location', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Administrator / administrar
    (1, 'logistics_maintenance', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Administrator / administrar
    (1, 'logistics_operator', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Administrator / administrar
    (1, 'logistics_quotation', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Administrator / administrar
    (1, 'logistics_rack', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Administrator / administrar
    (1, 'logistics_rate', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Administrator / administrar
    (1, 'logistics_receivable', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Administrator / administrar
    (1, 'logistics_service_request', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Administrator / administrar
    (1, 'logistics_shipment', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Administrator / administrar
    (1, 'logistics_trailer', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Administrator / administrar
    (1, 'logistics_trip', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Administrator / administrar
    (1, 'logistics_unit', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Administrator / administrar
    (1, 'logistics_warehouse', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Administrator / administrar
    (1, 'incident', 4, 4, 4, 4, 'sidebar', 'Operaciones', 'operations', 'Incidencias', 350, 'operaciones'),   -- Administrator / administrar
    (1, 'incident_detail', 4, 4, 4, 4, 'sidebar', 'Operaciones', 'operations', 'Detalle de incidencias', 360, 'operaciones'),   -- Administrator / administrar
    (1, 'incident_type', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Administrator / administrar
    (1, 'nm_incident_product', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Administrator / administrar
    (1, 'nm_template_task', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Administrator / administrar
    (1, 'proyect', 4, 4, 4, 4, 'sidebar', 'Operaciones', 'operations', 'Proyectos', 310, 'operaciones'),   -- Administrator / administrar
    (1, 'task', 4, 4, 4, 4, 'sidebar', 'Operaciones', 'operations', 'Tareas', 320, 'operaciones'),   -- Administrator / administrar
    (1, 'task_note', 4, 4, 4, 4, 'sidebar', 'Operaciones', 'operations', 'Notas de tarea', 330, 'operaciones'),   -- Administrator / administrar
    (1, 'task_type', 4, 4, 4, 4, 'sidebar', 'Operaciones', 'operations', 'Tipos de tarea', 340, 'operaciones'),   -- Administrator / administrar
    (1, 'template', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Administrator / administrar
    (1, 'payroll_concept', 4, 4, 4, 4, 'sidebar', 'Recursos humanos', 'hr', 'Conceptos', 720, 'rh'),   -- Administrator / administrar
    (1, 'payroll_detail', 4, 4, 4, 4, 'sidebar', 'Recursos humanos', 'hr', 'Detalle', 740, 'rh'),   -- Administrator / administrar
    (1, 'payroll_movement', 4, 4, 4, 4, 'sidebar', 'Recursos humanos', 'hr', 'Movimientos', 730, 'rh'),   -- Administrator / administrar
    (1, 'payroll_period', 4, 4, 4, 4, 'sidebar', 'Recursos humanos', 'hr', 'Periodos de nomina', 710, 'rh'),   -- Administrator / administrar
    (1, 'entity_permission', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 990, 'seguridad'),   -- Administrator / administrar
    (1, 'field', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 990, 'seguridad'),   -- Administrator / administrar
    (1, 'nm_field_permission', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 990, 'seguridad'),   -- Administrator / administrar
    (1, 'permission', 4, 4, 4, 4, 'sidebar', 'Seguridad', 'security', 'Perfiles', 920, 'seguridad'),   -- Administrator / administrar
    (1, 'user', 4, 4, 4, 4, 'sidebar', 'Seguridad', 'security', 'Usuarios', 910, 'seguridad'),   -- Administrator / administrar
    (1, 'incident_supervision', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Administrator / consultar
    (1, 'inventory_adjustment', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Administrator / consultar
    (1, 'kronos_device', 0, 4, 0, 0, 'settings', NULL, NULL, NULL, 790, 'rh'),   -- Administrator / consultar
    (1, 'multiemisor_csd', 4, 4, 4, 4, 'sidebar', 'Facturacion', 'billing', 'Multiemisor y CSD', 190, 'multiemisor_csd'),   -- Administrator / administrar
    (1, 'pos_admin', 4, 4, 4, 4, 'sidebar', 'Punto de venta', 'pos', 'Admin del punto de venta', 640, 'pos'),   -- Administrator / administrar
    (1, 'pos_terminal', 4, 4, 4, 0, 'sidebar', 'Punto de venta', 'pos', 'Caja del punto de venta', 640, 'pos'),   -- Administrator / capturar
    (1, 'project_authorization', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Administrator / consultar
    (1, 'project_execution', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Administrator / consultar
    (1, 'restaurant_admin', 4, 4, 4, 4, 'sidebar', 'Restaurante', 'restaurant', 'Admin del restaurante', 590, 'restaurante'),   -- Administrator / administrar
    (1, 'restaurant_cashier', 4, 4, 4, 0, 'sidebar', 'Restaurante', 'restaurant', 'Caja', 590, 'restaurante'),   -- Administrator / capturar
    (1, 'restaurant_kitchen', 0, 4, 4, 0, 'sidebar', 'Restaurante', 'restaurant', 'Cocina', 590, 'restaurante'),   -- Administrator / editar
    (1, 'restaurant_waiter', 4, 4, 4, 0, 'sidebar', 'Restaurante', 'restaurant', 'Meseros', 590, 'restaurante'),   -- Administrator / capturar
    (2, 'department', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Departamentos', 830, 'configuracion'),   -- gerente_administrativo / consultar
    (2, 'level', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Niveles', 850, 'configuracion'),   -- gerente_administrativo / consultar
    (2, 'status', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- gerente_administrativo / consultar
    (2, 'subdepartment', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Subdepartamentos', 840, 'configuracion'),   -- gerente_administrativo / consultar
    (2, 'theme', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- gerente_administrativo / consultar
    (2, 'appointment', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- gerente_administrativo / capturar
    (2, 'customer_supplier', 4, 4, 4, 0, 'sidebar', 'CRM', 'crm', 'Clientes y proveedores', 620, 'crm'),   -- gerente_administrativo / capturar
    (2, 'nm_survey_user', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- gerente_administrativo / capturar
    (2, 'product_sale_config', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- gerente_administrativo / capturar
    (2, 'public_api_key', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- gerente_administrativo / capturar
    (2, 'survey_multiple_answer', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- gerente_administrativo / capturar
    (2, 'survey_question', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- gerente_administrativo / capturar
    (2, 'bank', 4, 4, 4, 0, 'sidebar', 'Facturacion', 'billing', 'Bancos', 140, 'facturacion'),   -- gerente_administrativo / capturar
    (2, 'bank_account', 4, 4, 4, 0, 'sidebar', 'Facturacion', 'billing', 'Cuentas bancarias', 150, 'facturacion'),   -- gerente_administrativo / capturar
    (2, 'fiscal_account', 4, 4, 4, 0, 'sidebar', 'Facturacion', 'billing', 'Cuentas fiscales', 130, 'facturacion'),   -- gerente_administrativo / capturar
    (2, 'fiscal_record', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 190, 'facturacion'),   -- gerente_administrativo / capturar
    (2, 'fiscal_stamp', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 190, 'facturacion'),   -- gerente_administrativo / capturar
    (2, 'invoice', 4, 4, 4, 0, 'sidebar', 'Facturacion', 'billing', 'Facturas', 110, 'facturacion'),   -- gerente_administrativo / capturar
    (2, 'invoice_material_service', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 190, 'facturacion'),   -- gerente_administrativo / capturar
    (2, 'service', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 190, 'facturacion'),   -- gerente_administrativo / capturar
    (2, 'ticket', 4, 4, 4, 0, 'sidebar', 'Facturacion', 'billing', 'Tickets', 160, 'facturacion'),   -- gerente_administrativo / capturar
    (2, 'brand', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- gerente_administrativo / consultar
    (2, 'inventory_status', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- gerente_administrativo / consultar
    (2, 'location', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Ubicaciones', 220, 'inventario'),   -- gerente_administrativo / consultar
    (2, 'location_type', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Tipos de ubicacion', 230, 'inventario'),   -- gerente_administrativo / consultar
    (2, 'material', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Materiales', 240, 'inventario'),   -- gerente_administrativo / consultar
    (2, 'material_component', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Componentes', 260, 'inventario'),   -- gerente_administrativo / consultar
    (2, 'movement', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Movimientos', 250, 'inventario'),   -- gerente_administrativo / consultar
    (2, 'product', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Productos', 210, 'inventario'),   -- gerente_administrativo / consultar
    (2, 'product_family', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- gerente_administrativo / consultar
    (2, 'unit', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- gerente_administrativo / consultar
    (2, 'logistics_address', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- gerente_administrativo / consultar
    (2, 'logistics_branch', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- gerente_administrativo / consultar
    (2, 'logistics_contact', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- gerente_administrativo / consultar
    (2, 'logistics_contract', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- gerente_administrativo / consultar
    (2, 'logistics_evidence', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- gerente_administrativo / consultar
    (2, 'logistics_file', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- gerente_administrativo / consultar
    (2, 'logistics_incident', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- gerente_administrativo / consultar
    (2, 'logistics_inventory', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- gerente_administrativo / consultar
    (2, 'logistics_location', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- gerente_administrativo / consultar
    (2, 'logistics_maintenance', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- gerente_administrativo / consultar
    (2, 'logistics_operator', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- gerente_administrativo / consultar
    (2, 'logistics_quotation', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- gerente_administrativo / consultar
    (2, 'logistics_rack', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- gerente_administrativo / consultar
    (2, 'logistics_rate', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- gerente_administrativo / consultar
    (2, 'logistics_receivable', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- gerente_administrativo / consultar
    (2, 'logistics_service_request', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- gerente_administrativo / consultar
    (2, 'logistics_shipment', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- gerente_administrativo / consultar
    (2, 'logistics_trailer', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- gerente_administrativo / consultar
    (2, 'logistics_trip', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- gerente_administrativo / consultar
    (2, 'logistics_unit', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- gerente_administrativo / consultar
    (2, 'logistics_warehouse', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- gerente_administrativo / consultar
    (2, 'incident', 0, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Incidencias', 350, 'operaciones'),   -- gerente_administrativo / editar
    (2, 'incident_detail', 0, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Detalle de incidencias', 360, 'operaciones'),   -- gerente_administrativo / editar
    (2, 'incident_type', 0, 4, 4, 0, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- gerente_administrativo / editar
    (2, 'nm_incident_product', 0, 4, 4, 0, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- gerente_administrativo / editar
    (2, 'nm_template_task', 0, 4, 4, 0, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- gerente_administrativo / editar
    (2, 'proyect', 0, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Proyectos', 310, 'operaciones'),   -- gerente_administrativo / editar
    (2, 'task', 0, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Tareas', 320, 'operaciones'),   -- gerente_administrativo / editar
    (2, 'task_note', 0, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Notas de tarea', 330, 'operaciones'),   -- gerente_administrativo / editar
    (2, 'task_type', 0, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Tipos de tarea', 340, 'operaciones'),   -- gerente_administrativo / editar
    (2, 'template', 0, 4, 4, 0, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- gerente_administrativo / editar
    (2, 'payroll_concept', 4, 4, 4, 0, 'sidebar', 'Recursos humanos', 'hr', 'Conceptos', 720, 'rh'),   -- gerente_administrativo / capturar
    (2, 'payroll_detail', 4, 4, 4, 0, 'sidebar', 'Recursos humanos', 'hr', 'Detalle', 740, 'rh'),   -- gerente_administrativo / capturar
    (2, 'payroll_movement', 4, 4, 4, 0, 'sidebar', 'Recursos humanos', 'hr', 'Movimientos', 730, 'rh'),   -- gerente_administrativo / capturar
    (2, 'payroll_period', 4, 4, 4, 0, 'sidebar', 'Recursos humanos', 'hr', 'Periodos de nomina', 710, 'rh'),   -- gerente_administrativo / capturar
    (2, 'incident_supervision', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- gerente_administrativo / consultar
    (2, 'kronos_device', 0, 4, 0, 0, 'settings', NULL, NULL, NULL, 790, 'rh'),   -- gerente_administrativo / consultar
    (3, 'department', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Departamentos', 830, 'configuracion'),   -- vendedor / consultar
    (3, 'level', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Niveles', 850, 'configuracion'),   -- vendedor / consultar
    (3, 'status', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- vendedor / consultar
    (3, 'subdepartment', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Subdepartamentos', 840, 'configuracion'),   -- vendedor / consultar
    (3, 'theme', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- vendedor / consultar
    (3, 'appointment', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- vendedor / capturar
    (3, 'customer_supplier', 4, 4, 4, 0, 'sidebar', 'CRM', 'crm', 'Clientes y proveedores', 620, 'crm'),   -- vendedor / capturar
    (3, 'nm_survey_user', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- vendedor / capturar
    (3, 'product_sale_config', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- vendedor / capturar
    (3, 'public_api_key', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- vendedor / capturar
    (3, 'survey_multiple_answer', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- vendedor / capturar
    (3, 'survey_question', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- vendedor / capturar
    (3, 'bank', 4, 4, 4, 0, 'sidebar', 'Facturacion', 'billing', 'Bancos', 140, 'facturacion'),   -- vendedor / capturar
    (3, 'bank_account', 4, 4, 4, 0, 'sidebar', 'Facturacion', 'billing', 'Cuentas bancarias', 150, 'facturacion'),   -- vendedor / capturar
    (3, 'fiscal_account', 4, 4, 4, 0, 'sidebar', 'Facturacion', 'billing', 'Cuentas fiscales', 130, 'facturacion'),   -- vendedor / capturar
    (3, 'fiscal_record', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 190, 'facturacion'),   -- vendedor / capturar
    (3, 'fiscal_stamp', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 190, 'facturacion'),   -- vendedor / capturar
    (3, 'invoice', 4, 4, 4, 0, 'sidebar', 'Facturacion', 'billing', 'Facturas', 110, 'facturacion'),   -- vendedor / capturar
    (3, 'invoice_material_service', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 190, 'facturacion'),   -- vendedor / capturar
    (3, 'service', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 190, 'facturacion'),   -- vendedor / capturar
    (3, 'ticket', 4, 4, 4, 0, 'sidebar', 'Facturacion', 'billing', 'Tickets', 160, 'facturacion'),   -- vendedor / capturar
    (3, 'brand', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- vendedor / consultar
    (3, 'inventory_status', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- vendedor / consultar
    (3, 'location', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Ubicaciones', 220, 'inventario'),   -- vendedor / consultar
    (3, 'location_type', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Tipos de ubicacion', 230, 'inventario'),   -- vendedor / consultar
    (3, 'material', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Materiales', 240, 'inventario'),   -- vendedor / consultar
    (3, 'material_component', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Componentes', 260, 'inventario'),   -- vendedor / consultar
    (3, 'movement', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Movimientos', 250, 'inventario'),   -- vendedor / consultar
    (3, 'product', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Productos', 210, 'inventario'),   -- vendedor / consultar
    (3, 'product_family', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- vendedor / consultar
    (3, 'unit', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- vendedor / consultar
    (10, 'department', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Departamentos', 830, 'configuracion'),   -- Mesero / consultar
    (10, 'level', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Niveles', 850, 'configuracion'),   -- Mesero / consultar
    (10, 'status', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Mesero / consultar
    (10, 'subdepartment', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Subdepartamentos', 840, 'configuracion'),   -- Mesero / consultar
    (10, 'theme', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Mesero / consultar
    (10, 'restaurant_waiter', 4, 4, 4, 0, 'sidebar', 'Restaurante', 'restaurant', 'Meseros', 590, 'restaurante'),   -- Mesero / capturar
    (11, 'department', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Departamentos', 830, 'configuracion'),   -- Cocina / consultar
    (11, 'level', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Niveles', 850, 'configuracion'),   -- Cocina / consultar
    (11, 'status', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Cocina / consultar
    (11, 'subdepartment', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Subdepartamentos', 840, 'configuracion'),   -- Cocina / consultar
    (11, 'theme', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Cocina / consultar
    (11, 'restaurant_kitchen', 0, 4, 4, 0, 'sidebar', 'Restaurante', 'restaurant', 'Cocina', 590, 'restaurante'),   -- Cocina / editar
    (12, 'department', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Departamentos', 830, 'configuracion'),   -- Caja Restaurante / consultar
    (12, 'level', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Niveles', 850, 'configuracion'),   -- Caja Restaurante / consultar
    (12, 'status', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Caja Restaurante / consultar
    (12, 'subdepartment', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Subdepartamentos', 840, 'configuracion'),   -- Caja Restaurante / consultar
    (12, 'theme', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Caja Restaurante / consultar
    (12, 'restaurant_cashier', 4, 4, 4, 0, 'sidebar', 'Restaurante', 'restaurant', 'Caja', 590, 'restaurante'),   -- Caja Restaurante / capturar
    (13, 'department', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Departamentos', 830, 'configuracion'),   -- Admin Restaurante / consultar
    (13, 'level', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Niveles', 850, 'configuracion'),   -- Admin Restaurante / consultar
    (13, 'status', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Admin Restaurante / consultar
    (13, 'subdepartment', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Subdepartamentos', 840, 'configuracion'),   -- Admin Restaurante / consultar
    (13, 'theme', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Admin Restaurante / consultar
    (13, 'restaurant_admin', 4, 4, 4, 4, 'sidebar', 'Restaurante', 'restaurant', 'Admin del restaurante', 590, 'restaurante'),   -- Admin Restaurante / administrar
    (13, 'restaurant_cashier', 4, 4, 4, 0, 'sidebar', 'Restaurante', 'restaurant', 'Caja', 590, 'restaurante'),   -- Admin Restaurante / capturar
    (13, 'restaurant_kitchen', 0, 4, 4, 0, 'sidebar', 'Restaurante', 'restaurant', 'Cocina', 590, 'restaurante'),   -- Admin Restaurante / editar
    (13, 'restaurant_waiter', 4, 4, 4, 0, 'sidebar', 'Restaurante', 'restaurant', 'Meseros', 590, 'restaurante'),   -- Admin Restaurante / capturar
    (14, 'department', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Departamentos', 830, 'configuracion'),   -- Jefe de taller / consultar
    (14, 'level', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Niveles', 850, 'configuracion'),   -- Jefe de taller / consultar
    (14, 'status', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Jefe de taller / consultar
    (14, 'subdepartment', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Subdepartamentos', 840, 'configuracion'),   -- Jefe de taller / consultar
    (14, 'theme', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Jefe de taller / consultar
    (14, 'brand', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Jefe de taller / consultar
    (14, 'inventory_status', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Jefe de taller / consultar
    (14, 'location', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Ubicaciones', 220, 'inventario'),   -- Jefe de taller / consultar
    (14, 'location_type', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Tipos de ubicacion', 230, 'inventario'),   -- Jefe de taller / consultar
    (14, 'material', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Materiales', 240, 'inventario'),   -- Jefe de taller / consultar
    (14, 'material_component', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Componentes', 260, 'inventario'),   -- Jefe de taller / consultar
    (14, 'movement', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Movimientos', 250, 'inventario'),   -- Jefe de taller / consultar
    (14, 'product', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Productos', 210, 'inventario'),   -- Jefe de taller / consultar
    (14, 'product_family', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Jefe de taller / consultar
    (14, 'unit', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Jefe de taller / consultar
    (14, 'incident', 4, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Incidencias', 350, 'operaciones'),   -- Jefe de taller / capturar
    (14, 'incident_detail', 4, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Detalle de incidencias', 360, 'operaciones'),   -- Jefe de taller / capturar
    (14, 'incident_type', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Jefe de taller / capturar
    (14, 'nm_incident_product', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Jefe de taller / capturar
    (14, 'nm_template_task', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Jefe de taller / capturar
    (14, 'proyect', 4, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Proyectos', 310, 'operaciones'),   -- Jefe de taller / capturar
    (14, 'task', 4, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Tareas', 320, 'operaciones'),   -- Jefe de taller / capturar
    (14, 'task_note', 4, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Notas de tarea', 330, 'operaciones'),   -- Jefe de taller / capturar
    (14, 'task_type', 4, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Tipos de tarea', 340, 'operaciones'),   -- Jefe de taller / capturar
    (14, 'template', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Jefe de taller / capturar
    (14, 'incident_supervision', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Jefe de taller / consultar
    (14, 'project_execution', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Jefe de taller / consultar
    (15, 'department', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Departamentos', 830, 'configuracion'),   -- Supervisor / consultar
    (15, 'level', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Niveles', 850, 'configuracion'),   -- Supervisor / consultar
    (15, 'status', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Supervisor / consultar
    (15, 'subdepartment', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Subdepartamentos', 840, 'configuracion'),   -- Supervisor / consultar
    (15, 'theme', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Supervisor / consultar
    (15, 'brand', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Supervisor / consultar
    (15, 'inventory_status', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Supervisor / consultar
    (15, 'location', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Ubicaciones', 220, 'inventario'),   -- Supervisor / consultar
    (15, 'location_type', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Tipos de ubicacion', 230, 'inventario'),   -- Supervisor / consultar
    (15, 'material', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Materiales', 240, 'inventario'),   -- Supervisor / consultar
    (15, 'material_component', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Componentes', 260, 'inventario'),   -- Supervisor / consultar
    (15, 'movement', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Movimientos', 250, 'inventario'),   -- Supervisor / consultar
    (15, 'product', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Productos', 210, 'inventario'),   -- Supervisor / consultar
    (15, 'product_family', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Supervisor / consultar
    (15, 'unit', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Supervisor / consultar
    (15, 'incident', 4, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Incidencias', 350, 'operaciones'),   -- Supervisor / capturar
    (15, 'incident_detail', 4, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Detalle de incidencias', 360, 'operaciones'),   -- Supervisor / capturar
    (15, 'incident_type', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Supervisor / capturar
    (15, 'nm_incident_product', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Supervisor / capturar
    (15, 'nm_template_task', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Supervisor / capturar
    (15, 'proyect', 4, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Proyectos', 310, 'operaciones'),   -- Supervisor / capturar
    (15, 'task', 4, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Tareas', 320, 'operaciones'),   -- Supervisor / capturar
    (15, 'task_note', 4, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Notas de tarea', 330, 'operaciones'),   -- Supervisor / capturar
    (15, 'task_type', 4, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Tipos de tarea', 340, 'operaciones'),   -- Supervisor / capturar
    (15, 'template', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Supervisor / capturar
    (15, 'incident_supervision', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Supervisor / consultar
    (16, 'department', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Departamentos', 830, 'configuracion'),   -- Gerente / consultar
    (16, 'level', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Niveles', 850, 'configuracion'),   -- Gerente / consultar
    (16, 'status', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Gerente / consultar
    (16, 'subdepartment', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Subdepartamentos', 840, 'configuracion'),   -- Gerente / consultar
    (16, 'theme', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Gerente / consultar
    (16, 'appointment', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- Gerente / capturar
    (16, 'customer_supplier', 4, 4, 4, 0, 'sidebar', 'CRM', 'crm', 'Clientes y proveedores', 620, 'crm'),   -- Gerente / capturar
    (16, 'nm_survey_user', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- Gerente / capturar
    (16, 'product_sale_config', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- Gerente / capturar
    (16, 'public_api_key', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- Gerente / capturar
    (16, 'survey_multiple_answer', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- Gerente / capturar
    (16, 'survey_question', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- Gerente / capturar
    (16, 'bank', 4, 4, 4, 0, 'sidebar', 'Facturacion', 'billing', 'Bancos', 140, 'facturacion'),   -- Gerente / capturar
    (16, 'bank_account', 4, 4, 4, 0, 'sidebar', 'Facturacion', 'billing', 'Cuentas bancarias', 150, 'facturacion'),   -- Gerente / capturar
    (16, 'fiscal_account', 4, 4, 4, 0, 'sidebar', 'Facturacion', 'billing', 'Cuentas fiscales', 130, 'facturacion'),   -- Gerente / capturar
    (16, 'fiscal_record', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 190, 'facturacion'),   -- Gerente / capturar
    (16, 'fiscal_stamp', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 190, 'facturacion'),   -- Gerente / capturar
    (16, 'invoice', 4, 4, 4, 0, 'sidebar', 'Facturacion', 'billing', 'Facturas', 110, 'facturacion'),   -- Gerente / capturar
    (16, 'invoice_material_service', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 190, 'facturacion'),   -- Gerente / capturar
    (16, 'service', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 190, 'facturacion'),   -- Gerente / capturar
    (16, 'ticket', 4, 4, 4, 0, 'sidebar', 'Facturacion', 'billing', 'Tickets', 160, 'facturacion'),   -- Gerente / capturar
    (16, 'brand', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Gerente / consultar
    (16, 'inventory_status', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Gerente / consultar
    (16, 'location', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Ubicaciones', 220, 'inventario'),   -- Gerente / consultar
    (16, 'location_type', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Tipos de ubicacion', 230, 'inventario'),   -- Gerente / consultar
    (16, 'material', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Materiales', 240, 'inventario'),   -- Gerente / consultar
    (16, 'material_component', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Componentes', 260, 'inventario'),   -- Gerente / consultar
    (16, 'movement', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Movimientos', 250, 'inventario'),   -- Gerente / consultar
    (16, 'product', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Productos', 210, 'inventario'),   -- Gerente / consultar
    (16, 'product_family', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Gerente / consultar
    (16, 'unit', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Gerente / consultar
    (16, 'logistics_address', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Gerente / consultar
    (16, 'logistics_branch', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Gerente / consultar
    (16, 'logistics_contact', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Gerente / consultar
    (16, 'logistics_contract', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Gerente / consultar
    (16, 'logistics_evidence', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Gerente / consultar
    (16, 'logistics_file', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Gerente / consultar
    (16, 'logistics_incident', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Gerente / consultar
    (16, 'logistics_inventory', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Gerente / consultar
    (16, 'logistics_location', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Gerente / consultar
    (16, 'logistics_maintenance', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Gerente / consultar
    (16, 'logistics_operator', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Gerente / consultar
    (16, 'logistics_quotation', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Gerente / consultar
    (16, 'logistics_rack', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Gerente / consultar
    (16, 'logistics_rate', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Gerente / consultar
    (16, 'logistics_receivable', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Gerente / consultar
    (16, 'logistics_service_request', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Gerente / consultar
    (16, 'logistics_shipment', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Gerente / consultar
    (16, 'logistics_trailer', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Gerente / consultar
    (16, 'logistics_trip', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Gerente / consultar
    (16, 'logistics_unit', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Gerente / consultar
    (16, 'logistics_warehouse', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Gerente / consultar
    (16, 'incident', 0, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Incidencias', 350, 'operaciones'),   -- Gerente / editar
    (16, 'incident_detail', 0, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Detalle de incidencias', 360, 'operaciones'),   -- Gerente / editar
    (16, 'incident_type', 0, 4, 4, 0, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Gerente / editar
    (16, 'nm_incident_product', 0, 4, 4, 0, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Gerente / editar
    (16, 'nm_template_task', 0, 4, 4, 0, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Gerente / editar
    (16, 'proyect', 0, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Proyectos', 310, 'operaciones'),   -- Gerente / editar
    (16, 'task', 0, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Tareas', 320, 'operaciones'),   -- Gerente / editar
    (16, 'task_note', 0, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Notas de tarea', 330, 'operaciones'),   -- Gerente / editar
    (16, 'task_type', 0, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Tipos de tarea', 340, 'operaciones'),   -- Gerente / editar
    (16, 'template', 0, 4, 4, 0, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Gerente / editar
    (16, 'payroll_concept', 0, 4, 0, 0, 'sidebar', 'Recursos humanos', 'hr', 'Conceptos', 720, 'rh'),   -- Gerente / consultar
    (16, 'payroll_detail', 0, 4, 0, 0, 'sidebar', 'Recursos humanos', 'hr', 'Detalle', 740, 'rh'),   -- Gerente / consultar
    (16, 'payroll_movement', 0, 4, 0, 0, 'sidebar', 'Recursos humanos', 'hr', 'Movimientos', 730, 'rh'),   -- Gerente / consultar
    (16, 'payroll_period', 0, 4, 0, 0, 'sidebar', 'Recursos humanos', 'hr', 'Periodos de nomina', 710, 'rh'),   -- Gerente / consultar
    (16, 'incident_supervision', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Gerente / consultar
    (16, 'project_authorization', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Gerente / consultar
    (17, 'department', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Departamentos', 830, 'configuracion'),   -- Almacenista / consultar
    (17, 'level', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Niveles', 850, 'configuracion'),   -- Almacenista / consultar
    (17, 'status', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Almacenista / consultar
    (17, 'subdepartment', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Subdepartamentos', 840, 'configuracion'),   -- Almacenista / consultar
    (17, 'theme', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Almacenista / consultar
    (17, 'brand', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Almacenista / capturar
    (17, 'inventory_status', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Almacenista / capturar
    (17, 'location', 4, 4, 4, 0, 'sidebar', 'Inventario', 'inventory', 'Ubicaciones', 220, 'inventario'),   -- Almacenista / capturar
    (17, 'location_type', 4, 4, 4, 0, 'sidebar', 'Inventario', 'inventory', 'Tipos de ubicacion', 230, 'inventario'),   -- Almacenista / capturar
    (17, 'material', 4, 4, 4, 0, 'sidebar', 'Inventario', 'inventory', 'Materiales', 240, 'inventario'),   -- Almacenista / capturar
    (17, 'material_component', 4, 4, 4, 0, 'sidebar', 'Inventario', 'inventory', 'Componentes', 260, 'inventario'),   -- Almacenista / capturar
    (17, 'movement', 4, 4, 4, 0, 'sidebar', 'Inventario', 'inventory', 'Movimientos', 250, 'inventario'),   -- Almacenista / capturar
    (17, 'product', 4, 4, 4, 0, 'sidebar', 'Inventario', 'inventory', 'Productos', 210, 'inventario'),   -- Almacenista / capturar
    (17, 'product_family', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Almacenista / capturar
    (17, 'unit', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Almacenista / capturar
    (18, 'department', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Departamentos', 830, 'configuracion'),   -- Jefe de almacen / consultar
    (18, 'level', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Niveles', 850, 'configuracion'),   -- Jefe de almacen / consultar
    (18, 'status', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Jefe de almacen / consultar
    (18, 'subdepartment', 0, 4, 0, 0, 'sidebar', 'Configuracion', 'settings', 'Subdepartamentos', 840, 'configuracion'),   -- Jefe de almacen / consultar
    (18, 'theme', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Jefe de almacen / consultar
    (18, 'brand', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Jefe de almacen / administrar
    (18, 'inventory_status', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Jefe de almacen / administrar
    (18, 'location', 4, 4, 4, 4, 'sidebar', 'Inventario', 'inventory', 'Ubicaciones', 220, 'inventario'),   -- Jefe de almacen / administrar
    (18, 'location_type', 4, 4, 4, 4, 'sidebar', 'Inventario', 'inventory', 'Tipos de ubicacion', 230, 'inventario'),   -- Jefe de almacen / administrar
    (18, 'material', 4, 4, 4, 4, 'sidebar', 'Inventario', 'inventory', 'Materiales', 240, 'inventario'),   -- Jefe de almacen / administrar
    (18, 'material_component', 4, 4, 4, 4, 'sidebar', 'Inventario', 'inventory', 'Componentes', 260, 'inventario'),   -- Jefe de almacen / administrar
    (18, 'movement', 4, 4, 4, 4, 'sidebar', 'Inventario', 'inventory', 'Movimientos', 250, 'inventario'),   -- Jefe de almacen / administrar
    (18, 'product', 4, 4, 4, 4, 'sidebar', 'Inventario', 'inventory', 'Productos', 210, 'inventario'),   -- Jefe de almacen / administrar
    (18, 'product_family', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Jefe de almacen / administrar
    (18, 'unit', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Jefe de almacen / administrar
    (18, 'logistics_address', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Jefe de almacen / capturar
    (18, 'logistics_branch', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Jefe de almacen / capturar
    (18, 'logistics_contact', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Jefe de almacen / capturar
    (18, 'logistics_contract', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Jefe de almacen / capturar
    (18, 'logistics_evidence', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Jefe de almacen / capturar
    (18, 'logistics_file', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Jefe de almacen / capturar
    (18, 'logistics_incident', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Jefe de almacen / capturar
    (18, 'logistics_inventory', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Jefe de almacen / capturar
    (18, 'logistics_location', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Jefe de almacen / capturar
    (18, 'logistics_maintenance', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Jefe de almacen / capturar
    (18, 'logistics_operator', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Jefe de almacen / capturar
    (18, 'logistics_quotation', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Jefe de almacen / capturar
    (18, 'logistics_rack', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Jefe de almacen / capturar
    (18, 'logistics_rate', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Jefe de almacen / capturar
    (18, 'logistics_receivable', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Jefe de almacen / capturar
    (18, 'logistics_service_request', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Jefe de almacen / capturar
    (18, 'logistics_shipment', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Jefe de almacen / capturar
    (18, 'logistics_trailer', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Jefe de almacen / capturar
    (18, 'logistics_trip', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Jefe de almacen / capturar
    (18, 'logistics_unit', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Jefe de almacen / capturar
    (18, 'logistics_warehouse', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 490, 'logistica'),   -- Jefe de almacen / capturar
    (18, 'inventory_adjustment', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 290, 'inventario')   -- Jefe de almacen / consultar
) AS v (id_permission, entity_name, scope_create, scope_read, scope_update, scope_delete, menu_location,
        menu_group, menu_group_icon, menu_label, menu_order, modulo_licencia)
WHERE EXISTS (SELECT 1 FROM permission p WHERE p.id_permission = v.id_permission)
  AND (
    v.modulo_licencia IN ('configuracion', 'seguridad')
    OR licensed_modules = ''
    OR licensed_modules IS NULL
    OR v.modulo_licencia = ANY(string_to_array(licensed_modules, ','))
  )
-- La restriccion unica es por (perfil, entidad) sin importar la baja logica, y
-- aqui NO se toca la fila que ya existe: ni sus bits, ni su navegacion, ni su
-- baja.
--
-- Una fila viva es del gestor: pisarla revierte el trabajo del administrador.
-- Una fila de baja significa que la quitaron a proposito -desde este cambio el
-- gestor la marca de baja en vez de borrarla-, asi que reactivarla seria
-- devolver un acceso que alguien decidio retirar.
--
-- Se siembra, entonces, solo el par (perfil, entidad) que no existe todavia:
-- un modulo nuevo, una entidad nueva, un rol nuevo. Eso es "sembrar lo que
-- falta".
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
