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
-- 13 modulos, 5 roles, 16 capacidades,
-- 256 filas.
--
--   facturacion      9 entidades
--     Administrator (administrar), Gerente (capturar)
--   inventario      11 entidades  [almacen propio]
--     Administrator (administrar), Supervisor (consultar), Gerente (consultar), Almacenista (capturar), Jefe de almacen (administrar)
--   operaciones     10 entidades
--     Administrator (administrar), Supervisor (capturar), Gerente (editar)
--   logistica       21 entidades  [almacen propio]
--     Administrator (administrar), Gerente (consultar), Jefe de almacen (capturar)
--   restaurante      0 entidades  [almacen propio]
--     Administrator (administrar)
--   pos              0 entidades
--     Administrator (administrar)
--   crm              7 entidades
--     Administrator (administrar), Gerente (capturar)
--   documentos       4 entidades
--     Administrator (administrar)
--   laboratorio      3 entidades
--     Administrator (administrar)
--   rh               4 entidades
--     Administrator (administrar), Gerente (consultar)
--   kpis             4 entidades
--     Administrator (administrar)
--   configuracion    5 entidades
--     Administrator (administrar), Supervisor (consultar), Gerente (consultar), Almacenista (consultar), Jefe de almacen (consultar)
--   seguridad        7 entidades
--     Administrator (administrar)

BEGIN;

-- NO se marca de baja lo vigente antes de sembrar.
--
-- Lo hacia, y corria en cada reinicio del pod: cualquier ajuste hecho desde el
-- gestor de roles se revertia en el siguiente despliegue. Medido antes del
-- cambio: un permiso subido de 2 a 15 en el gestor volvia a 2 al reaplicar.
--
-- La decision es que el gestor manda y el registro solo siembra lo que falta.
-- El registro sigue dando los valores POR OMISION -lo que recibe un modulo o un
-- rol nuevo- y deja de ser la fuente de la verdad sobre quien puede que.
--
-- Retirar un modulo cuando cambia la licencia ya no necesita borrar filas: el
-- plan se comprueba en cada peticion y filtra el menu, asi que un modulo fuera
-- del plan es inalcanzable aunque su fila exista. Ver `app/modules/plan.py`.

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

-- Los roles que el registro declara, creados si esta base no los tiene.
--
-- Los escribia `database/seed.sql` a mano, y por eso una instalacion nueva
-- salia con los identificadores cruzados: el archivo ocupaba los ids 2 y 3 con
-- 'gerente_administrativo' y 'vendedor' -dos perfiles que el negocio no
-- reconoce- y empujaba a Supervisor y Gerente a numeros altos. El desastre que
-- eso causo en clientes reales esta documentado en
-- 20260908100000_roles_con_los_ids_de_la_base.sql.
--
-- Se crea por NOMBRE, no por numero: si el rol ya existe -con el id que sea- no
-- se toca nada. El id del registro solo se usa cuando ESTA LIBRE, que es el
-- caso de una instalacion nueva, para que los numeros salgan como el registro
-- los documenta. Nunca se mueve un rol existente de identificador: los
-- usuarios apuntan ahi, y moverlos es mover permisos de gente real.
--
-- Corregido 2026-09-24: el NOT EXISTS de nombre filtraba solo filas ACTIVAS
-- (`AND p.deletion_date IS NULL`). Es el mismo patron fantasma que
-- `b4a80cb` ya encontro y corrigio en `20260828150000_warehouse_roles.sql`
-- para "Jefe de almacen": si un rol de esta lista se retira (baja logica),
-- cada reinicio del pod deja de ver una fila activa con ese nombre y crea
-- una nueva -- fantasma, para siempre. "Existe" ahora significa que el
-- nombre aparecio alguna vez, activo o de baja; una resiembra no debe
-- resucitar un rol que alguien retiro a proposito.
INSERT INTO permission (
    id_permission, created_by, authorized_by, permission_description,
    id_department, id_subdepartment, id_level
)
SELECT r.id_permission, 1, 1, r.role_name, 1, 1, 1
  FROM (VALUES
    (1, 'Administrator'),
    (2, 'Supervisor'),
    (3, 'Gerente'),
    (5, 'Almacenista'),
    (6, 'Jefe de almacen')
       ) AS r(id_permission, role_name)
 WHERE NOT EXISTS (
         SELECT 1 FROM permission p
          WHERE lower(p.permission_description) = lower(r.role_name)
       )
   AND NOT EXISTS (
         SELECT 1 FROM permission p WHERE p.id_permission = r.id_permission
       );

-- El mismo rol, cuando su numero del registro ya lo ocupa otro. Deja que la
-- secuencia asigne uno: lo que importa es que el rol exista y se llame como el
-- registro dice, porque la matriz de abajo resuelve por nombre.
INSERT INTO permission (
    created_by, authorized_by, permission_description,
    id_department, id_subdepartment, id_level
)
SELECT 1, 1, r.role_name, 1, 1, 1
  FROM (VALUES
    (1, 'Administrator'),
    (2, 'Supervisor'),
    (3, 'Gerente'),
    (5, 'Almacenista'),
    (6, 'Jefe de almacen')
       ) AS r(id_permission, role_name)
 WHERE NOT EXISTS (
         SELECT 1 FROM permission p
          WHERE lower(p.permission_description) = lower(r.role_name)
       );

-- Los INSERT de arriba fijan identificadores explicitos, lo que NO avanza la
-- secuencia. Sin realinearla, el siguiente rol que alguien cree desde la
-- pantalla choca contra una llave ya usada.
SELECT setval(
    pg_get_serial_sequence('permission', 'id_permission'),
    GREATEST((SELECT MAX(id_permission) FROM permission), 1)
);

-- La matriz se resuelve por NOMBRE de rol, no por id_permission fijo.
--
-- Version anterior de este archivo escribia el numero de `id_permission`
-- directo en las VALUES, asumiendo que ese numero significa lo mismo en
-- cualquier instalacion. Es falso: los ids de `permission` dependen del
-- orden en que cada base sembro sus roles. Medido en dos ambientes reales
-- con la version vieja: en un cliente, el id que aqui se penso como
-- "gerente_administrativo" resulto ser de verdad "Supervisor", y Facturacion
-- se concedio a un rol operativo que nunca debia tenerla; en otro cliente, un
-- numero distinto choco con "Almacenista" en vez de con el rol pensado.
--
-- Se guarda la matriz completa (con el NOMBRE de cada rol, no su numero) en
-- una tabla temporal para no repetir las 300+ filas dos veces -una para
-- limpiar lo viejo, otra para sembrar lo nuevo-: ambos pasos hacen JOIN
-- contra `permission.permission_description` para resolver el id real de
-- ESTA base.
CREATE TEMP TABLE matriz_de_permisos AS
SELECT * FROM (VALUES
    ('Administrator', 'department', 15, 'settings', 'Configuracion', 'settings', 'Departamentos', 830, 'configuracion'),   -- Administrator / administrar
    ('Administrator', 'level', 15, 'settings', 'Configuracion', 'settings', 'Niveles', 850, 'configuracion'),   -- Administrator / administrar
    ('Administrator', 'status', 15, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Administrator / administrar
    ('Administrator', 'subdepartment', 15, 'settings', 'Configuracion', 'settings', 'Subdepartamentos', 840, 'configuracion'),   -- Administrator / administrar
    ('Administrator', 'theme', 15, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Administrator / administrar
    ('Administrator', 'appointment', 15, 'sidebar', 'CRM', 'crm', 'Calendario', 630, 'crm'),   -- Administrator / administrar
    ('Administrator', 'customer_supplier', 15, 'sidebar', 'CRM', 'crm', 'Clientes y proveedores', 620, 'crm'),   -- Administrator / administrar
    ('Administrator', 'nm_survey_user', 15, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- Administrator / administrar
    ('Administrator', 'product_sale_config', 15, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- Administrator / administrar
    ('Administrator', 'public_api_key', 15, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- Administrator / administrar
    ('Administrator', 'survey_multiple_answer', 15, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- Administrator / administrar
    ('Administrator', 'survey_question', 15, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- Administrator / administrar
    ('Administrator', 'document', 15, 'sidebar', 'Documentos', 'file-text', 'Documentos', 660, 'documentos'),   -- Administrator / administrar
    ('Administrator', 'document_category', 15, 'sidebar', 'Documentos', 'file-text', 'Categorias de documento', 670, 'documentos'),   -- Administrator / administrar
    ('Administrator', 'document_relation', 15, 'hidden', NULL, NULL, NULL, 740, 'documentos'),   -- Administrator / administrar
    ('Administrator', 'document_version', 15, 'hidden', NULL, NULL, NULL, 740, 'documentos'),   -- Administrator / administrar
    ('Administrator', 'bank', 15, 'sidebar', 'Facturacion', 'billing', 'Bancos', 140, 'facturacion'),   -- Administrator / administrar
    ('Administrator', 'bank_account', 15, 'sidebar', 'Facturacion', 'billing', 'Cuentas bancarias', 150, 'facturacion'),   -- Administrator / administrar
    ('Administrator', 'fiscal_account', 15, 'sidebar', 'Facturacion', 'billing', 'Cuentas fiscales', 130, 'facturacion'),   -- Administrator / administrar
    ('Administrator', 'fiscal_record', 15, 'hidden', NULL, NULL, NULL, 190, 'facturacion'),   -- Administrator / administrar
    ('Administrator', 'fiscal_stamp', 15, 'hidden', NULL, NULL, NULL, 190, 'facturacion'),   -- Administrator / administrar
    ('Administrator', 'invoice', 15, 'sidebar', 'Facturacion', 'billing', 'Facturas', 110, 'facturacion'),   -- Administrator / administrar
    ('Administrator', 'invoice_material_service', 15, 'hidden', NULL, NULL, NULL, 190, 'facturacion'),   -- Administrator / administrar
    ('Administrator', 'service', 15, 'hidden', NULL, NULL, NULL, 190, 'facturacion'),   -- Administrator / administrar
    ('Administrator', 'ticket', 15, 'sidebar', 'Facturacion', 'billing', 'Tickets', 160, 'facturacion'),   -- Administrator / administrar
    ('Administrator', 'brand', 15, 'sidebar', 'Inventario', 'inventory', 'Marcas', 214, 'inventario'),   -- Administrator / administrar
    ('Administrator', 'inventory_status', 15, 'sidebar', 'Inventario', 'inventory', 'Estado de inventario', 270, 'inventario'),   -- Administrator / administrar
    ('Administrator', 'location', 15, 'sidebar', 'Inventario', 'inventory', 'Ubicaciones', 220, 'inventario'),   -- Administrator / administrar
    ('Administrator', 'location_type', 15, 'sidebar', 'Inventario', 'inventory', 'Tipos de ubicacion', 230, 'inventario'),   -- Administrator / administrar
    ('Administrator', 'material', 15, 'sidebar', 'Inventario', 'inventory', 'Materiales', 240, 'inventario'),   -- Administrator / administrar
    ('Administrator', 'material_attribute', 15, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Administrator / administrar
    ('Administrator', 'material_component', 15, 'sidebar', 'Inventario', 'inventory', 'Componentes', 260, 'inventario'),   -- Administrator / administrar
    ('Administrator', 'movement', 15, 'sidebar', 'Inventario', 'inventory', 'Movimientos', 250, 'inventario'),   -- Administrator / administrar
    ('Administrator', 'product', 15, 'sidebar', 'Inventario', 'inventory', 'Productos', 210, 'inventario'),   -- Administrator / administrar
    ('Administrator', 'product_family', 15, 'sidebar', 'Inventario', 'inventory', 'Familias de producto', 212, 'inventario'),   -- Administrator / administrar
    ('Administrator', 'unit', 15, 'sidebar', 'Inventario', 'inventory', 'Unidades', 216, 'inventario'),   -- Administrator / administrar
    ('Administrator', 'kpi_dashboard', 15, 'hidden', NULL, NULL, NULL, 840, 'kpis'),   -- Administrator / administrar
    ('Administrator', 'kpi_dashboard_widget', 15, 'hidden', NULL, NULL, NULL, 840, 'kpis'),   -- Administrator / administrar
    ('Administrator', 'kpi_definition', 15, 'hidden', NULL, NULL, NULL, 840, 'kpis'),   -- Administrator / administrar
    ('Administrator', 'nm_permission_kpi', 15, 'hidden', NULL, NULL, NULL, 840, 'kpis'),   -- Administrator / administrar
    ('Administrator', 'laboratory_equipment', 15, 'sidebar', 'Laboratorio', 'flask-conical', 'Equipos', 680, 'laboratorio'),   -- Administrator / administrar
    ('Administrator', 'laboratory_service_order', 15, 'sidebar', 'Laboratorio', 'flask-conical', 'Ordenes de servicio', 670, 'laboratorio'),   -- Administrator / administrar
    ('Administrator', 'laboratory_service_order_status_history', 15, 'hidden', NULL, NULL, NULL, 750, 'laboratorio'),   -- Administrator / administrar
    ('Administrator', 'logistics_address', 15, 'sidebar', 'Logistica', 'logistics', 'Direcciones', 412, 'logistica'),   -- Administrator / administrar
    ('Administrator', 'logistics_branch', 15, 'sidebar', 'Logistica', 'logistics', 'Sucursales', 410, 'logistica'),   -- Administrator / administrar
    ('Administrator', 'logistics_contact', 15, 'sidebar', 'Logistica', 'logistics', 'Contactos', 414, 'logistica'),   -- Administrator / administrar
    ('Administrator', 'logistics_contract', 15, 'sidebar', 'Logistica', 'logistics', 'Contratos', 416, 'logistica'),   -- Administrator / administrar
    ('Administrator', 'logistics_evidence', 15, 'sidebar', 'Logistica', 'logistics', 'Evidencias', 446, 'logistica'),   -- Administrator / administrar
    ('Administrator', 'logistics_file', 15, 'sidebar', 'Logistica', 'logistics', 'Expedientes', 462, 'logistica'),   -- Administrator / administrar
    ('Administrator', 'logistics_incident', 15, 'sidebar', 'Logistica', 'logistics', 'Incidencias', 448, 'logistica'),   -- Administrator / administrar
    ('Administrator', 'logistics_inventory', 15, 'sidebar', 'Logistica', 'logistics', 'Inventario', 436, 'logistica'),   -- Administrator / administrar
    ('Administrator', 'logistics_location', 15, 'sidebar', 'Logistica', 'logistics', 'Ubicaciones', 432, 'logistica'),   -- Administrator / administrar
    ('Administrator', 'logistics_maintenance', 15, 'sidebar', 'Logistica', 'logistics', 'Mantenimientos', 456, 'logistica'),   -- Administrator / administrar
    ('Administrator', 'logistics_operator', 15, 'sidebar', 'Logistica', 'logistics', 'Operadores', 454, 'logistica'),   -- Administrator / administrar
    ('Administrator', 'logistics_quotation', 15, 'sidebar', 'Logistica', 'logistics', 'Cotizaciones', 420, 'logistica'),   -- Administrator / administrar
    ('Administrator', 'logistics_rack', 15, 'sidebar', 'Logistica', 'logistics', 'Racks', 434, 'logistica'),   -- Administrator / administrar
    ('Administrator', 'logistics_rate', 15, 'sidebar', 'Logistica', 'logistics', 'Tarifas', 418, 'logistica'),   -- Administrator / administrar
    ('Administrator', 'logistics_receivable', 15, 'sidebar', 'Logistica', 'logistics', 'Cuentas por cobrar', 460, 'logistica'),   -- Administrator / administrar
    ('Administrator', 'logistics_service_request', 15, 'sidebar', 'Logistica', 'logistics', 'Solicitudes de servicio', 440, 'logistica'),   -- Administrator / administrar
    ('Administrator', 'logistics_shipment', 15, 'sidebar', 'Logistica', 'logistics', 'Embarques', 444, 'logistica'),   -- Administrator / administrar
    ('Administrator', 'logistics_trailer', 15, 'sidebar', 'Logistica', 'logistics', 'Remolques', 452, 'logistica'),   -- Administrator / administrar
    ('Administrator', 'logistics_trip', 15, 'sidebar', 'Logistica', 'logistics', 'Viajes', 442, 'logistica'),   -- Administrator / administrar
    ('Administrator', 'logistics_unit', 15, 'sidebar', 'Logistica', 'logistics', 'Unidades', 450, 'logistica'),   -- Administrator / administrar
    ('Administrator', 'logistics_warehouse', 15, 'sidebar', 'Logistica', 'logistics', 'Almacenes', 430, 'logistica'),   -- Administrator / administrar
    ('Administrator', 'incident', 15, 'sidebar', 'Operaciones', 'operations', 'Incidencias', 330, 'operaciones'),   -- Administrator / administrar
    ('Administrator', 'incident_detail', 15, 'sidebar', 'Operaciones', 'operations', 'Subtipos de incidencia', 334, 'operaciones'),   -- Administrator / administrar
    ('Administrator', 'incident_type', 15, 'sidebar', 'Operaciones', 'operations', 'Tipos de incidencia', 332, 'operaciones'),   -- Administrator / administrar
    ('Administrator', 'nm_incident_product', 15, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Administrator / administrar
    ('Administrator', 'nm_template_task', 15, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Administrator / administrar
    ('Administrator', 'proyect', 15, 'sidebar', 'Operaciones', 'operations', 'Proyectos', 310, 'operaciones'),   -- Administrator / administrar
    ('Administrator', 'task', 15, 'sidebar', 'Operaciones', 'operations', 'Tareas', 320, 'operaciones'),   -- Administrator / administrar
    ('Administrator', 'task_note', 15, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Administrator / administrar
    ('Administrator', 'task_type', 15, 'sidebar', 'Operaciones', 'operations', 'Tipos de tarea', 342, 'operaciones'),   -- Administrator / administrar
    ('Administrator', 'template', 15, 'sidebar', 'Operaciones', 'operations', 'Plantillas de tarea', 340, 'operaciones'),   -- Administrator / administrar
    ('Administrator', 'payroll_concept', 15, 'sidebar', 'Recursos humanos', 'hr', 'Conceptos', 720, 'rh'),   -- Administrator / administrar
    ('Administrator', 'payroll_detail', 15, 'sidebar', 'Recursos humanos', 'hr', 'Detalle', 740, 'rh'),   -- Administrator / administrar
    ('Administrator', 'payroll_movement', 15, 'sidebar', 'Recursos humanos', 'hr', 'Movimientos', 730, 'rh'),   -- Administrator / administrar
    ('Administrator', 'payroll_period', 15, 'sidebar', 'Recursos humanos', 'hr', 'Periodos de nomina', 710, 'rh'),   -- Administrator / administrar
    ('Administrator', 'entity_permission', 15, 'hidden', NULL, NULL, NULL, 990, 'seguridad'),   -- Administrator / administrar
    ('Administrator', 'field', 15, 'hidden', NULL, NULL, NULL, 990, 'seguridad'),   -- Administrator / administrar
    ('Administrator', 'nm_field_permission', 15, 'hidden', NULL, NULL, NULL, 990, 'seguridad'),   -- Administrator / administrar
    ('Administrator', 'permission', 15, 'settings', 'Configuracion', 'settings', 'Perfiles', 920, 'seguridad'),   -- Administrator / administrar
    ('Administrator', 'user', 15, 'settings', 'Configuracion', 'settings', 'Usuarios', 910, 'seguridad'),   -- Administrator / administrar
    ('Administrator', 'incident_supervision', 2, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Administrator / consultar
    ('Administrator', 'inventory_adjustment', 2, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Administrator / consultar
    ('Administrator', 'kronos_device', 2, 'settings', 'Recursos humanos', 'hr', 'Conexion al dispositivo Kronos', 790, 'rh'),   -- Administrator / consultar
    ('Administrator', 'multiemisor_csd', 15, 'sidebar', 'Facturacion', 'billing', 'Multiemisor y CSD', 190, 'multiemisor_csd'),   -- Administrator / administrar
    ('Administrator', 'pos_admin', 15, 'sidebar', 'Punto de venta', 'pos', 'Admin del punto de venta', 640, 'pos'),   -- Administrator / administrar
    ('Administrator', 'pos_terminal', 7, 'sidebar', 'Punto de venta', 'pos', 'Caja del punto de venta', 640, 'pos'),   -- Administrator / capturar
    ('Administrator', 'project_authorization', 2, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Administrator / consultar
    ('Administrator', 'project_execution', 2, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Administrator / consultar
    ('Administrator', 'restaurant_admin', 15, 'sidebar', 'Restaurante', 'restaurant', 'Admin del restaurante', 590, 'restaurante'),   -- Administrator / administrar
    ('Administrator', 'restaurant_cashier', 7, 'sidebar', 'Restaurante', 'restaurant', 'Caja', 590, 'restaurante'),   -- Administrator / capturar
    ('Administrator', 'restaurant_kitchen', 6, 'sidebar', 'Restaurante', 'restaurant', 'Cocina', 590, 'restaurante'),   -- Administrator / editar
    ('Administrator', 'restaurant_waiter', 7, 'sidebar', 'Restaurante', 'restaurant', 'Meseros', 590, 'restaurante'),   -- Administrator / capturar
    ('Administrator', 'warehouse_prevoucher', 7, 'sidebar', 'Inventario', 'inventory', 'Prevales de material', 290, 'inventario'),   -- Administrator / capturar
    ('Administrator', 'warehouse_voucher_confirm', 2, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Administrator / consultar
    ('Supervisor', 'department', 2, 'settings', 'Configuracion', 'settings', 'Departamentos', 830, 'configuracion'),   -- Supervisor / consultar
    ('Supervisor', 'level', 2, 'settings', 'Configuracion', 'settings', 'Niveles', 850, 'configuracion'),   -- Supervisor / consultar
    ('Supervisor', 'status', 2, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Supervisor / consultar
    ('Supervisor', 'subdepartment', 2, 'settings', 'Configuracion', 'settings', 'Subdepartamentos', 840, 'configuracion'),   -- Supervisor / consultar
    ('Supervisor', 'theme', 2, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Supervisor / consultar
    ('Supervisor', 'brand', 2, 'sidebar', 'Inventario', 'inventory', 'Marcas', 214, 'inventario'),   -- Supervisor / consultar
    ('Supervisor', 'inventory_status', 2, 'sidebar', 'Inventario', 'inventory', 'Estado de inventario', 270, 'inventario'),   -- Supervisor / consultar
    ('Supervisor', 'location', 2, 'sidebar', 'Inventario', 'inventory', 'Ubicaciones', 220, 'inventario'),   -- Supervisor / consultar
    ('Supervisor', 'location_type', 2, 'sidebar', 'Inventario', 'inventory', 'Tipos de ubicacion', 230, 'inventario'),   -- Supervisor / consultar
    ('Supervisor', 'material', 2, 'sidebar', 'Inventario', 'inventory', 'Materiales', 240, 'inventario'),   -- Supervisor / consultar
    ('Supervisor', 'material_attribute', 2, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Supervisor / consultar
    ('Supervisor', 'material_component', 2, 'sidebar', 'Inventario', 'inventory', 'Componentes', 260, 'inventario'),   -- Supervisor / consultar
    ('Supervisor', 'movement', 2, 'sidebar', 'Inventario', 'inventory', 'Movimientos', 250, 'inventario'),   -- Supervisor / consultar
    ('Supervisor', 'product', 2, 'sidebar', 'Inventario', 'inventory', 'Productos', 210, 'inventario'),   -- Supervisor / consultar
    ('Supervisor', 'product_family', 2, 'sidebar', 'Inventario', 'inventory', 'Familias de producto', 212, 'inventario'),   -- Supervisor / consultar
    ('Supervisor', 'unit', 2, 'sidebar', 'Inventario', 'inventory', 'Unidades', 216, 'inventario'),   -- Supervisor / consultar
    ('Supervisor', 'incident', 7, 'sidebar', 'Operaciones', 'operations', 'Incidencias', 330, 'operaciones'),   -- Supervisor / capturar
    ('Supervisor', 'incident_detail', 7, 'sidebar', 'Operaciones', 'operations', 'Subtipos de incidencia', 334, 'operaciones'),   -- Supervisor / capturar
    ('Supervisor', 'incident_type', 7, 'sidebar', 'Operaciones', 'operations', 'Tipos de incidencia', 332, 'operaciones'),   -- Supervisor / capturar
    ('Supervisor', 'nm_incident_product', 7, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Supervisor / capturar
    ('Supervisor', 'nm_template_task', 7, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Supervisor / capturar
    ('Supervisor', 'proyect', 7, 'sidebar', 'Operaciones', 'operations', 'Proyectos', 310, 'operaciones'),   -- Supervisor / capturar
    ('Supervisor', 'task', 7, 'sidebar', 'Operaciones', 'operations', 'Tareas', 320, 'operaciones'),   -- Supervisor / capturar
    ('Supervisor', 'task_note', 7, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Supervisor / capturar
    ('Supervisor', 'task_type', 7, 'sidebar', 'Operaciones', 'operations', 'Tipos de tarea', 342, 'operaciones'),   -- Supervisor / capturar
    ('Supervisor', 'template', 7, 'sidebar', 'Operaciones', 'operations', 'Plantillas de tarea', 340, 'operaciones'),   -- Supervisor / capturar
    ('Supervisor', 'incident_supervision', 2, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Supervisor / consultar
    ('Supervisor', 'project_execution', 2, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Supervisor / consultar
    ('Supervisor', 'warehouse_prevoucher', 7, 'sidebar', 'Inventario', 'inventory', 'Prevales de material', 290, 'inventario'),   -- Supervisor / capturar
    ('Gerente', 'department', 2, 'settings', 'Configuracion', 'settings', 'Departamentos', 830, 'configuracion'),   -- Gerente / consultar
    ('Gerente', 'level', 2, 'settings', 'Configuracion', 'settings', 'Niveles', 850, 'configuracion'),   -- Gerente / consultar
    ('Gerente', 'status', 2, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Gerente / consultar
    ('Gerente', 'subdepartment', 2, 'settings', 'Configuracion', 'settings', 'Subdepartamentos', 840, 'configuracion'),   -- Gerente / consultar
    ('Gerente', 'theme', 2, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Gerente / consultar
    ('Gerente', 'appointment', 7, 'sidebar', 'CRM', 'crm', 'Calendario', 630, 'crm'),   -- Gerente / capturar
    ('Gerente', 'customer_supplier', 7, 'sidebar', 'CRM', 'crm', 'Clientes y proveedores', 620, 'crm'),   -- Gerente / capturar
    ('Gerente', 'nm_survey_user', 7, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- Gerente / capturar
    ('Gerente', 'product_sale_config', 7, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- Gerente / capturar
    ('Gerente', 'public_api_key', 7, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- Gerente / capturar
    ('Gerente', 'survey_multiple_answer', 7, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- Gerente / capturar
    ('Gerente', 'survey_question', 7, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- Gerente / capturar
    ('Gerente', 'bank', 7, 'sidebar', 'Facturacion', 'billing', 'Bancos', 140, 'facturacion'),   -- Gerente / capturar
    ('Gerente', 'bank_account', 7, 'sidebar', 'Facturacion', 'billing', 'Cuentas bancarias', 150, 'facturacion'),   -- Gerente / capturar
    ('Gerente', 'fiscal_account', 7, 'sidebar', 'Facturacion', 'billing', 'Cuentas fiscales', 130, 'facturacion'),   -- Gerente / capturar
    ('Gerente', 'fiscal_record', 7, 'hidden', NULL, NULL, NULL, 190, 'facturacion'),   -- Gerente / capturar
    ('Gerente', 'fiscal_stamp', 7, 'hidden', NULL, NULL, NULL, 190, 'facturacion'),   -- Gerente / capturar
    ('Gerente', 'invoice', 7, 'sidebar', 'Facturacion', 'billing', 'Facturas', 110, 'facturacion'),   -- Gerente / capturar
    ('Gerente', 'invoice_material_service', 7, 'hidden', NULL, NULL, NULL, 190, 'facturacion'),   -- Gerente / capturar
    ('Gerente', 'service', 7, 'hidden', NULL, NULL, NULL, 190, 'facturacion'),   -- Gerente / capturar
    ('Gerente', 'ticket', 7, 'sidebar', 'Facturacion', 'billing', 'Tickets', 160, 'facturacion'),   -- Gerente / capturar
    ('Gerente', 'brand', 2, 'sidebar', 'Inventario', 'inventory', 'Marcas', 214, 'inventario'),   -- Gerente / consultar
    ('Gerente', 'inventory_status', 2, 'sidebar', 'Inventario', 'inventory', 'Estado de inventario', 270, 'inventario'),   -- Gerente / consultar
    ('Gerente', 'location', 2, 'sidebar', 'Inventario', 'inventory', 'Ubicaciones', 220, 'inventario'),   -- Gerente / consultar
    ('Gerente', 'location_type', 2, 'sidebar', 'Inventario', 'inventory', 'Tipos de ubicacion', 230, 'inventario'),   -- Gerente / consultar
    ('Gerente', 'material', 2, 'sidebar', 'Inventario', 'inventory', 'Materiales', 240, 'inventario'),   -- Gerente / consultar
    ('Gerente', 'material_attribute', 2, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Gerente / consultar
    ('Gerente', 'material_component', 2, 'sidebar', 'Inventario', 'inventory', 'Componentes', 260, 'inventario'),   -- Gerente / consultar
    ('Gerente', 'movement', 2, 'sidebar', 'Inventario', 'inventory', 'Movimientos', 250, 'inventario'),   -- Gerente / consultar
    ('Gerente', 'product', 2, 'sidebar', 'Inventario', 'inventory', 'Productos', 210, 'inventario'),   -- Gerente / consultar
    ('Gerente', 'product_family', 2, 'sidebar', 'Inventario', 'inventory', 'Familias de producto', 212, 'inventario'),   -- Gerente / consultar
    ('Gerente', 'unit', 2, 'sidebar', 'Inventario', 'inventory', 'Unidades', 216, 'inventario'),   -- Gerente / consultar
    ('Gerente', 'logistics_address', 2, 'sidebar', 'Logistica', 'logistics', 'Direcciones', 412, 'logistica'),   -- Gerente / consultar
    ('Gerente', 'logistics_branch', 2, 'sidebar', 'Logistica', 'logistics', 'Sucursales', 410, 'logistica'),   -- Gerente / consultar
    ('Gerente', 'logistics_contact', 2, 'sidebar', 'Logistica', 'logistics', 'Contactos', 414, 'logistica'),   -- Gerente / consultar
    ('Gerente', 'logistics_contract', 2, 'sidebar', 'Logistica', 'logistics', 'Contratos', 416, 'logistica'),   -- Gerente / consultar
    ('Gerente', 'logistics_evidence', 2, 'sidebar', 'Logistica', 'logistics', 'Evidencias', 446, 'logistica'),   -- Gerente / consultar
    ('Gerente', 'logistics_file', 2, 'sidebar', 'Logistica', 'logistics', 'Expedientes', 462, 'logistica'),   -- Gerente / consultar
    ('Gerente', 'logistics_incident', 2, 'sidebar', 'Logistica', 'logistics', 'Incidencias', 448, 'logistica'),   -- Gerente / consultar
    ('Gerente', 'logistics_inventory', 2, 'sidebar', 'Logistica', 'logistics', 'Inventario', 436, 'logistica'),   -- Gerente / consultar
    ('Gerente', 'logistics_location', 2, 'sidebar', 'Logistica', 'logistics', 'Ubicaciones', 432, 'logistica'),   -- Gerente / consultar
    ('Gerente', 'logistics_maintenance', 2, 'sidebar', 'Logistica', 'logistics', 'Mantenimientos', 456, 'logistica'),   -- Gerente / consultar
    ('Gerente', 'logistics_operator', 2, 'sidebar', 'Logistica', 'logistics', 'Operadores', 454, 'logistica'),   -- Gerente / consultar
    ('Gerente', 'logistics_quotation', 2, 'sidebar', 'Logistica', 'logistics', 'Cotizaciones', 420, 'logistica'),   -- Gerente / consultar
    ('Gerente', 'logistics_rack', 2, 'sidebar', 'Logistica', 'logistics', 'Racks', 434, 'logistica'),   -- Gerente / consultar
    ('Gerente', 'logistics_rate', 2, 'sidebar', 'Logistica', 'logistics', 'Tarifas', 418, 'logistica'),   -- Gerente / consultar
    ('Gerente', 'logistics_receivable', 2, 'sidebar', 'Logistica', 'logistics', 'Cuentas por cobrar', 460, 'logistica'),   -- Gerente / consultar
    ('Gerente', 'logistics_service_request', 2, 'sidebar', 'Logistica', 'logistics', 'Solicitudes de servicio', 440, 'logistica'),   -- Gerente / consultar
    ('Gerente', 'logistics_shipment', 2, 'sidebar', 'Logistica', 'logistics', 'Embarques', 444, 'logistica'),   -- Gerente / consultar
    ('Gerente', 'logistics_trailer', 2, 'sidebar', 'Logistica', 'logistics', 'Remolques', 452, 'logistica'),   -- Gerente / consultar
    ('Gerente', 'logistics_trip', 2, 'sidebar', 'Logistica', 'logistics', 'Viajes', 442, 'logistica'),   -- Gerente / consultar
    ('Gerente', 'logistics_unit', 2, 'sidebar', 'Logistica', 'logistics', 'Unidades', 450, 'logistica'),   -- Gerente / consultar
    ('Gerente', 'logistics_warehouse', 2, 'sidebar', 'Logistica', 'logistics', 'Almacenes', 430, 'logistica'),   -- Gerente / consultar
    ('Gerente', 'incident', 6, 'sidebar', 'Operaciones', 'operations', 'Incidencias', 330, 'operaciones'),   -- Gerente / editar
    ('Gerente', 'incident_detail', 6, 'sidebar', 'Operaciones', 'operations', 'Subtipos de incidencia', 334, 'operaciones'),   -- Gerente / editar
    ('Gerente', 'incident_type', 6, 'sidebar', 'Operaciones', 'operations', 'Tipos de incidencia', 332, 'operaciones'),   -- Gerente / editar
    ('Gerente', 'nm_incident_product', 6, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Gerente / editar
    ('Gerente', 'nm_template_task', 6, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Gerente / editar
    ('Gerente', 'proyect', 6, 'sidebar', 'Operaciones', 'operations', 'Proyectos', 310, 'operaciones'),   -- Gerente / editar
    ('Gerente', 'task', 6, 'sidebar', 'Operaciones', 'operations', 'Tareas', 320, 'operaciones'),   -- Gerente / editar
    ('Gerente', 'task_note', 6, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Gerente / editar
    ('Gerente', 'task_type', 6, 'sidebar', 'Operaciones', 'operations', 'Tipos de tarea', 342, 'operaciones'),   -- Gerente / editar
    ('Gerente', 'template', 6, 'sidebar', 'Operaciones', 'operations', 'Plantillas de tarea', 340, 'operaciones'),   -- Gerente / editar
    ('Gerente', 'payroll_concept', 2, 'sidebar', 'Recursos humanos', 'hr', 'Conceptos', 720, 'rh'),   -- Gerente / consultar
    ('Gerente', 'payroll_detail', 2, 'sidebar', 'Recursos humanos', 'hr', 'Detalle', 740, 'rh'),   -- Gerente / consultar
    ('Gerente', 'payroll_movement', 2, 'sidebar', 'Recursos humanos', 'hr', 'Movimientos', 730, 'rh'),   -- Gerente / consultar
    ('Gerente', 'payroll_period', 2, 'sidebar', 'Recursos humanos', 'hr', 'Periodos de nomina', 710, 'rh'),   -- Gerente / consultar
    ('Gerente', 'incident_supervision', 2, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Gerente / consultar
    ('Gerente', 'pos_admin', 15, 'sidebar', 'Punto de venta', 'pos', 'Admin del punto de venta', 640, 'pos'),   -- Gerente / administrar
    ('Gerente', 'pos_terminal', 7, 'sidebar', 'Punto de venta', 'pos', 'Caja del punto de venta', 640, 'pos'),   -- Gerente / capturar
    ('Gerente', 'project_authorization', 2, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Gerente / consultar
    ('Almacenista', 'department', 2, 'settings', 'Configuracion', 'settings', 'Departamentos', 830, 'configuracion'),   -- Almacenista / consultar
    ('Almacenista', 'level', 2, 'settings', 'Configuracion', 'settings', 'Niveles', 850, 'configuracion'),   -- Almacenista / consultar
    ('Almacenista', 'status', 2, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Almacenista / consultar
    ('Almacenista', 'subdepartment', 2, 'settings', 'Configuracion', 'settings', 'Subdepartamentos', 840, 'configuracion'),   -- Almacenista / consultar
    ('Almacenista', 'theme', 2, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Almacenista / consultar
    ('Almacenista', 'brand', 7, 'sidebar', 'Inventario', 'inventory', 'Marcas', 214, 'inventario'),   -- Almacenista / capturar
    ('Almacenista', 'inventory_status', 7, 'sidebar', 'Inventario', 'inventory', 'Estado de inventario', 270, 'inventario'),   -- Almacenista / capturar
    ('Almacenista', 'location', 7, 'sidebar', 'Inventario', 'inventory', 'Ubicaciones', 220, 'inventario'),   -- Almacenista / capturar
    ('Almacenista', 'location_type', 7, 'sidebar', 'Inventario', 'inventory', 'Tipos de ubicacion', 230, 'inventario'),   -- Almacenista / capturar
    ('Almacenista', 'material', 7, 'sidebar', 'Inventario', 'inventory', 'Materiales', 240, 'inventario'),   -- Almacenista / capturar
    ('Almacenista', 'material_attribute', 7, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Almacenista / capturar
    ('Almacenista', 'material_component', 7, 'sidebar', 'Inventario', 'inventory', 'Componentes', 260, 'inventario'),   -- Almacenista / capturar
    ('Almacenista', 'movement', 7, 'sidebar', 'Inventario', 'inventory', 'Movimientos', 250, 'inventario'),   -- Almacenista / capturar
    ('Almacenista', 'product', 7, 'sidebar', 'Inventario', 'inventory', 'Productos', 210, 'inventario'),   -- Almacenista / capturar
    ('Almacenista', 'product_family', 7, 'sidebar', 'Inventario', 'inventory', 'Familias de producto', 212, 'inventario'),   -- Almacenista / capturar
    ('Almacenista', 'unit', 7, 'sidebar', 'Inventario', 'inventory', 'Unidades', 216, 'inventario'),   -- Almacenista / capturar
    ('Almacenista', 'warehouse_voucher', 7, 'sidebar', 'Inventario', 'inventory', 'Vales de almacen', 290, 'inventario'),   -- Almacenista / capturar
    ('Almacenista', 'warehouse_voucher_confirm', 2, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Almacenista / consultar
    ('Jefe de almacen', 'department', 2, 'settings', 'Configuracion', 'settings', 'Departamentos', 830, 'configuracion'),   -- Jefe de almacen / consultar
    ('Jefe de almacen', 'level', 2, 'settings', 'Configuracion', 'settings', 'Niveles', 850, 'configuracion'),   -- Jefe de almacen / consultar
    ('Jefe de almacen', 'status', 2, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Jefe de almacen / consultar
    ('Jefe de almacen', 'subdepartment', 2, 'settings', 'Configuracion', 'settings', 'Subdepartamentos', 840, 'configuracion'),   -- Jefe de almacen / consultar
    ('Jefe de almacen', 'theme', 2, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Jefe de almacen / consultar
    ('Jefe de almacen', 'brand', 15, 'sidebar', 'Inventario', 'inventory', 'Marcas', 214, 'inventario'),   -- Jefe de almacen / administrar
    ('Jefe de almacen', 'inventory_status', 15, 'sidebar', 'Inventario', 'inventory', 'Estado de inventario', 270, 'inventario'),   -- Jefe de almacen / administrar
    ('Jefe de almacen', 'location', 15, 'sidebar', 'Inventario', 'inventory', 'Ubicaciones', 220, 'inventario'),   -- Jefe de almacen / administrar
    ('Jefe de almacen', 'location_type', 15, 'sidebar', 'Inventario', 'inventory', 'Tipos de ubicacion', 230, 'inventario'),   -- Jefe de almacen / administrar
    ('Jefe de almacen', 'material', 15, 'sidebar', 'Inventario', 'inventory', 'Materiales', 240, 'inventario'),   -- Jefe de almacen / administrar
    ('Jefe de almacen', 'material_attribute', 15, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Jefe de almacen / administrar
    ('Jefe de almacen', 'material_component', 15, 'sidebar', 'Inventario', 'inventory', 'Componentes', 260, 'inventario'),   -- Jefe de almacen / administrar
    ('Jefe de almacen', 'movement', 15, 'sidebar', 'Inventario', 'inventory', 'Movimientos', 250, 'inventario'),   -- Jefe de almacen / administrar
    ('Jefe de almacen', 'product', 15, 'sidebar', 'Inventario', 'inventory', 'Productos', 210, 'inventario'),   -- Jefe de almacen / administrar
    ('Jefe de almacen', 'product_family', 15, 'sidebar', 'Inventario', 'inventory', 'Familias de producto', 212, 'inventario'),   -- Jefe de almacen / administrar
    ('Jefe de almacen', 'unit', 15, 'sidebar', 'Inventario', 'inventory', 'Unidades', 216, 'inventario'),   -- Jefe de almacen / administrar
    ('Jefe de almacen', 'logistics_address', 7, 'sidebar', 'Logistica', 'logistics', 'Direcciones', 412, 'logistica'),   -- Jefe de almacen / capturar
    ('Jefe de almacen', 'logistics_branch', 7, 'sidebar', 'Logistica', 'logistics', 'Sucursales', 410, 'logistica'),   -- Jefe de almacen / capturar
    ('Jefe de almacen', 'logistics_contact', 7, 'sidebar', 'Logistica', 'logistics', 'Contactos', 414, 'logistica'),   -- Jefe de almacen / capturar
    ('Jefe de almacen', 'logistics_contract', 7, 'sidebar', 'Logistica', 'logistics', 'Contratos', 416, 'logistica'),   -- Jefe de almacen / capturar
    ('Jefe de almacen', 'logistics_evidence', 7, 'sidebar', 'Logistica', 'logistics', 'Evidencias', 446, 'logistica'),   -- Jefe de almacen / capturar
    ('Jefe de almacen', 'logistics_file', 7, 'sidebar', 'Logistica', 'logistics', 'Expedientes', 462, 'logistica'),   -- Jefe de almacen / capturar
    ('Jefe de almacen', 'logistics_incident', 7, 'sidebar', 'Logistica', 'logistics', 'Incidencias', 448, 'logistica'),   -- Jefe de almacen / capturar
    ('Jefe de almacen', 'logistics_inventory', 7, 'sidebar', 'Logistica', 'logistics', 'Inventario', 436, 'logistica'),   -- Jefe de almacen / capturar
    ('Jefe de almacen', 'logistics_location', 7, 'sidebar', 'Logistica', 'logistics', 'Ubicaciones', 432, 'logistica'),   -- Jefe de almacen / capturar
    ('Jefe de almacen', 'logistics_maintenance', 7, 'sidebar', 'Logistica', 'logistics', 'Mantenimientos', 456, 'logistica'),   -- Jefe de almacen / capturar
    ('Jefe de almacen', 'logistics_operator', 7, 'sidebar', 'Logistica', 'logistics', 'Operadores', 454, 'logistica'),   -- Jefe de almacen / capturar
    ('Jefe de almacen', 'logistics_quotation', 7, 'sidebar', 'Logistica', 'logistics', 'Cotizaciones', 420, 'logistica'),   -- Jefe de almacen / capturar
    ('Jefe de almacen', 'logistics_rack', 7, 'sidebar', 'Logistica', 'logistics', 'Racks', 434, 'logistica'),   -- Jefe de almacen / capturar
    ('Jefe de almacen', 'logistics_rate', 7, 'sidebar', 'Logistica', 'logistics', 'Tarifas', 418, 'logistica'),   -- Jefe de almacen / capturar
    ('Jefe de almacen', 'logistics_receivable', 7, 'sidebar', 'Logistica', 'logistics', 'Cuentas por cobrar', 460, 'logistica'),   -- Jefe de almacen / capturar
    ('Jefe de almacen', 'logistics_service_request', 7, 'sidebar', 'Logistica', 'logistics', 'Solicitudes de servicio', 440, 'logistica'),   -- Jefe de almacen / capturar
    ('Jefe de almacen', 'logistics_shipment', 7, 'sidebar', 'Logistica', 'logistics', 'Embarques', 444, 'logistica'),   -- Jefe de almacen / capturar
    ('Jefe de almacen', 'logistics_trailer', 7, 'sidebar', 'Logistica', 'logistics', 'Remolques', 452, 'logistica'),   -- Jefe de almacen / capturar
    ('Jefe de almacen', 'logistics_trip', 7, 'sidebar', 'Logistica', 'logistics', 'Viajes', 442, 'logistica'),   -- Jefe de almacen / capturar
    ('Jefe de almacen', 'logistics_unit', 7, 'sidebar', 'Logistica', 'logistics', 'Unidades', 450, 'logistica'),   -- Jefe de almacen / capturar
    ('Jefe de almacen', 'logistics_warehouse', 7, 'sidebar', 'Logistica', 'logistics', 'Almacenes', 430, 'logistica'),   -- Jefe de almacen / capturar
    ('Jefe de almacen', 'inventory_adjustment', 2, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Jefe de almacen / consultar
    ('Jefe de almacen', 'warehouse_voucher', 7, 'sidebar', 'Inventario', 'inventory', 'Vales de almacen', 290, 'inventario'),   -- Jefe de almacen / capturar
    ('Jefe de almacen', 'warehouse_voucher_authorize', 7, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Jefe de almacen / capturar
    ('Jefe de almacen', 'warehouse_voucher_confirm', 2, 'hidden', NULL, NULL, NULL, 290, 'inventario')   -- Jefe de almacen / consultar
) AS v (role_name, entity_name, control_type, menu_location,
        menu_group, menu_group_icon, menu_label, menu_order, modulo_licencia);

-- Limpieza de lo que la version vieja (con id fijo) pudo haber sembrado en el
-- rol equivocado. Solo toca created_by=1 -nunca una fila que un
-- administrador haya ajustado desde el gestor de roles-, y solo entidades que
-- esta matriz gestiona: si el par (id_permission, entidad) que hoy existe no
-- es el que le corresponde por NOMBRE al rol que de verdad tiene ese id en
-- esta base, se borra. El INSERT de abajo la repone bien de inmediato.
DELETE FROM entity_permission ep
 WHERE ep.created_by = 1
   AND ep.entity_name IN (SELECT DISTINCT entity_name FROM matriz_de_permisos)
   AND NOT EXISTS (
     SELECT 1
       FROM matriz_de_permisos m
       JOIN permission p
         ON p.permission_description = m.role_name
        AND p.deletion_date IS NULL
      WHERE p.id_permission = ep.id_permission
        AND m.entity_name = ep.entity_name
        AND (
          m.modulo_licencia IN ('configuracion', 'seguridad')
          OR :'licensed_modules' = ''
          OR m.modulo_licencia = ANY(string_to_array(:'licensed_modules', ','))
        )
   );

-- `entity_permission.control_type` (mascara de bits: CREAR=1, LEER=2,
-- ACTUALIZAR=4, BORRAR=8) ya no existe -la elimino
-- 20260914110000_equipos_y_alcance_por_accion.sql, migracion posterior en la
-- cadena pero anterior en el tiempo de commit-. Se convierte aqui a las 4
-- columnas de alcance con la misma regla que uso esa migracion para los
-- datos existentes: bit encendido -> Todos (4), apagado -> Sin acceso (0). La
-- matriz de arriba se deja con la columna `control_type` tal cual -son 256
-- filas literales, y la conversion es mecanica- para no reescribir cada una
-- a mano.
INSERT INTO entity_permission (
    id_permission, entity_name, scope_create, scope_read, scope_update, scope_delete, menu_location,
    menu_group, menu_group_icon, menu_label, menu_order, created_by
)
SELECT p.id_permission, m.entity_name,
       CASE WHEN (m.control_type & 1) = 1 THEN 4 ELSE 0 END,
       CASE WHEN (m.control_type & 2) = 2 THEN 4 ELSE 0 END,
       CASE WHEN (m.control_type & 4) = 4 THEN 4 ELSE 0 END,
       CASE WHEN (m.control_type & 8) = 8 THEN 4 ELSE 0 END,
       m.menu_location,
       m.menu_group, m.menu_group_icon, m.menu_label, m.menu_order, 1
FROM matriz_de_permisos m
JOIN permission p
  ON p.permission_description = m.role_name
 AND p.deletion_date IS NULL
WHERE (
    m.modulo_licencia IN ('configuracion', 'seguridad')
    OR :'licensed_modules' = ''
    OR m.modulo_licencia = ANY(string_to_array(:'licensed_modules', ','))
  )
-- La restriccion unica es por (perfil, entidad) sin importar la baja logica, y
-- aqui NO se toca la fila que ya existe: ni sus bits, ni su navegacion, ni su
-- baja.
--
-- Una fila viva es del gestor: pisarla revierte el trabajo del administrador.
-- Una fila de baja significa que la quitaron a proposito -el gestor la marca de
-- baja en vez de borrarla-, asi que reactivarla devolveria un acceso retirado.
--
-- Se siembra solo el par (perfil, entidad) que no existe todavia: un modulo
-- nuevo, una entidad nueva, un rol nuevo. Eso es "sembrar lo que falta".
ON CONFLICT (id_permission, entity_name) DO NOTHING;

-- El catalogo de campos, poblado con las columnas REALES de cada entidad que
-- esta matriz gestiona.
--
-- Por que hacia falta
-- -------------------
-- `nm_field_permission` -- la tabla que decide que atributos ve un rol -- se
-- deriva mas abajo cruzando `entity_permission` con `field`. Si `field` no
-- tiene las columnas de una tabla, ese cruce no produce NADA para ella, y la
-- pantalla generica no pinta ni una columna porque solo muestra los campos
-- concedidos (`canSeeField` en el frontend).
--
-- Medido en la base antes de este cambio: `field` cubria 34 tablas, y eran casi
-- todas de logistica, documentos y laboratorio -- las que llegaron de ramas que
-- traian su propio sembrado. Inventario, facturacion, CRM, recursos humanos y
-- configuracion tenian CERO filas. El efecto real: un Almacenista abria
-- Productos y no veia ninguna columna, aunque su rol concede `product` en
-- CAPTURA; solo la cuenta de arranque veia algo, porque salta la comprobacion.
--
-- La fuente es `information_schema`, no una lista escrita a mano: una lista se
-- desfasa en cuanto alguien agrega una columna, que es exactamente como se
-- llego aqui. Las capacidades no aparecen porque no son tablas y el JOIN no las
-- encuentra, que es lo correcto: no tienen campos que conceder.
INSERT INTO field (table_name, field_name, created_by)
SELECT c.table_name, c.column_name, 1
  FROM information_schema.columns c
  JOIN (SELECT DISTINCT entity_name FROM matriz_de_permisos) m
    ON m.entity_name = c.table_name
 WHERE c.table_schema = 'public'
   -- Una capacidad NO es una tabla, aunque se llame como una.
   --
   -- `restaurant_waiter` es las dos cosas: la capacidad "Meseros" que concede
   -- la pantalla, y una tabla real del restaurante. Sin esta exclusion el
   -- cruce de arriba le poblaria campos a la capacidad -- y el gestor pediria
   -- marcar columnas de una tabla que esa capacidad no gobierna. La lista sale
   -- del registro, no escrita a mano, para que una capacidad nueva con nombre
   -- de tabla no vuelva a colarse.
   AND c.table_name NOT IN ('incident_supervision', 'inventory_adjustment', 'kronos_device', 'multiemisor_csd', 'pos_admin', 'pos_terminal', 'project_authorization', 'project_execution', 'restaurant_admin', 'restaurant_cashier', 'restaurant_kitchen', 'restaurant_waiter', 'warehouse_prevoucher', 'warehouse_voucher', 'warehouse_voucher_authorize', 'warehouse_voucher_confirm')
   -- Las administra el sistema: `created_by` lo fija el servicio con el
   -- usuario de la sesion, y las tres fechas las escribe el ORM. Publicarlas
   -- como configurables invita a capturarlas a mano.
   AND c.column_name NOT IN ('created_by', 'creation_date', 'last_update_date', 'deletion_date')
   AND NOT EXISTS (
     SELECT 1 FROM field f
      WHERE f.table_name = c.table_name
        AND f.field_name = c.column_name
        AND f.deletion_date IS NULL
   );

-- Y se retiran las columnas de sistema que sembrados anteriores si publicaron.
--
-- `field` traia 124 filas de `created_by`, `creation_date`, `last_update_date`
-- y `deletion_date` -- casi todas de logistica, documentos y laboratorio, que
-- llegaron con el sembrado de su propia rama. La pantalla ya las ocultaba, pero
-- la derivacion de mas abajo si les daba permiso, asi que cada rol cargaba
-- decenas de filas que no gobiernan nada.
UPDATE field f
   SET deletion_date = now(),
       last_update_date = now()
 WHERE f.deletion_date IS NULL
   AND f.field_name IN ('created_by', 'creation_date', 'last_update_date', 'deletion_date')
   AND EXISTS (SELECT 1 FROM matriz_de_permisos m WHERE m.entity_name = f.table_name);

-- Una columna que ya no existe en la tabla deja de ofrecerse. Se retira en
-- logico, como todo aqui, asi que el permiso que alguien le hubiera dado queda
-- para consulta. Si la columna vuelve, el INSERT de arriba la repone como fila
-- nueva en la siguiente corrida -- sin arrastrar los permisos de antes, que es
-- lo correcto: la columna de hoy puede no significar lo que significaba.
UPDATE field f
   SET deletion_date = now(),
       last_update_date = now()
 WHERE f.deletion_date IS NULL
   AND EXISTS (SELECT 1 FROM matriz_de_permisos m WHERE m.entity_name = f.table_name)
   AND f.table_name NOT IN ('incident_supervision', 'inventory_adjustment', 'kronos_device', 'multiemisor_csd', 'pos_admin', 'pos_terminal', 'project_authorization', 'project_execution', 'restaurant_admin', 'restaurant_cashier', 'restaurant_kitchen', 'restaurant_waiter', 'warehouse_prevoucher', 'warehouse_voucher', 'warehouse_voucher_authorize', 'warehouse_voucher_confirm')
   AND NOT EXISTS (
     SELECT 1 FROM information_schema.columns c
      WHERE c.table_schema = 'public'
        AND c.table_name = f.table_name
        AND c.column_name = f.field_name
   );

DROP TABLE matriz_de_permisos;

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
        -- Tambien cuenta la baja del CAMPO, no solo la de la entidad. Sin esta
        -- linea, retirar una columna del catalogo dejaba viva su concesion:
        -- eran las 124 filas de `created_by` y las tres fechas, que seguian
        -- concedidas despues de dar de baja el campo.
        AND f.deletion_date IS NULL
   );

INSERT INTO nm_field_permission (id_field, id_permission, control_type, created_by)
-- `entity_permission.control_type` (la mascara de bits de la que este valor
-- salia) ya no existe -ver la nota de mas arriba, en el INSERT de
-- `entity_permission`-. Se reconstruye el mismo bitmask desde las 4 columnas
-- de alcance: el bit se enciende si el alcance de esa accion es CUALQUIERA
-- que no sea "Sin acceso" (>0), que es lo que `control_type` ya decia -esta
-- tabla solo pregunta si el campo se puede ver/editar, no con que alcance.
SELECT f.id_field, ep.id_permission,
       LEAST(
           (CASE WHEN ep.scope_create > 0 THEN 1 ELSE 0 END) +
           (CASE WHEN ep.scope_read   > 0 THEN 2 ELSE 0 END) +
           (CASE WHEN ep.scope_update > 0 THEN 4 ELSE 0 END) +
           (CASE WHEN ep.scope_delete > 0 THEN 8 ELSE 0 END),
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

COMMIT;

