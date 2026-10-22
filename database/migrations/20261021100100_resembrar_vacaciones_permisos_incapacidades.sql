-- Resiembra del catalogo de permisos: vacaciones, permisos e incapacidades (2026-10-21).
--
-- Por que existe: el modulo `rh` agrego a `registry.py` la entidad
-- `employee_leave` (migracion 20261021100000). Sin estas filas de
-- `entity_permission` nadie podria registrar ni consultar ausencias: las rutas
-- contestarian 403. Ademas re-deriva el catalogo `field` y los permisos por campo
-- para las columnas nuevas de `employee_leave` y `payroll_detail`.
--
-- Quien recibe que, tal como lo declara el registro: Administrator administra y
-- Gerente consulta, igual que el resto de `rh`. Sin entrada de menu ("hidden"):
-- se capturan en la pantalla propia /employee_leaves.
--
-- Como el resto de las resiembras: ON CONFLICT DO NOTHING / WHERE NOT EXISTS. Solo
-- AGREGA las filas nuevas; el Gestor de roles y permisos manda sobre lo que ya
-- existe y no se toca ninguna columna scope_*.
--
-- Regenerado al juntar initAlan (2026-10-22): el sembrado de abajo sale del
-- registro combinado, donde "Gerente" ya es "Gerente general" (consulta RH) y
-- "Gerente tecnico" (sin RH) -- ver 20261021090000. Corre despues de esa
-- migracion, asi que si conservara el "Gerente" de antes volveria a crear ese
-- rol vacio en cada arranque.
--
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
-- 14 modulos, 7 roles, 22 capacidades,
-- 367 filas.
--
--   facturacion      9 entidades
--     Administrator (administrar), Gerente general (consultar)
--   inventario      11 entidades  [almacen propio]
--     Administrator (administrar), Supervisor (consultar), Gerente general (consultar), Gerente tecnico (consultar), Jefe de taller (consultar), Almacenista (administrar), Compras (consultar)
--   compras          2 entidades
--     Administrator (administrar), Gerente general (capturar), Gerente tecnico (consultar), Almacenista (consultar), Compras (capturar)
--   operaciones     11 entidades
--     Administrator (administrar), Supervisor (capturar), Gerente general (consultar), Gerente tecnico (editar), Jefe de taller (capturar), Compras (consultar)
--   logistica       21 entidades  [almacen propio]
--     Administrator (administrar), Gerente general (consultar), Almacenista (capturar)
--   restaurante      0 entidades  [almacen propio]
--     Administrator (administrar)
--   pos              0 entidades
--     Administrator (administrar)
--   crm              8 entidades
--     Administrator (administrar), Gerente general (consultar)
--   documentos       4 entidades
--     Administrator (administrar)
--   laboratorio      3 entidades
--     Administrator (administrar)
--   rh              13 entidades
--     Administrator (administrar), Gerente general (consultar)
--   kpis             4 entidades
--     Administrator (administrar)
--   configuracion    5 entidades
--     Administrator (administrar), Supervisor (consultar), Gerente general (consultar), Gerente tecnico (consultar), Jefe de taller (consultar), Almacenista (consultar), Compras (consultar)
--   seguridad        9 entidades
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
-- Se crea por NOMBRE, no por numero: si el rol ya existe -con el id que sea,
-- ACTIVO O DE BAJA- no se toca nada. Comprobar solo lo activo resucitaria en
-- cada reinicio del pod cualquier rol que un administrador haya retirado a
-- proposito desde el gestor -la unica fila que quedaria seria la de baja, "no
-- existe" volveria a ser cierto, y este INSERT la recrearia sin fin-. El id
-- del registro solo se usa cuando ESTA LIBRE, que es el caso de una
-- instalacion nueva, para que los numeros salgan como el registro los
-- documenta. Nunca se mueve un rol existente de identificador: los usuarios
-- apuntan ahi, y moverlos es mover permisos de gente real.
INSERT INTO permission (
    id_permission, created_by, authorized_by, permission_description,
    id_department, id_subdepartment, id_level
)
SELECT r.id_permission, 1, 1, r.role_name, 1, 1, 1
  FROM (VALUES
    (1, 'Administrator'),
    (2, 'Supervisor'),
    (9, 'Gerente general'),
    (3, 'Gerente tecnico'),
    (4, 'Jefe de taller'),
    (5, 'Almacenista'),
    (8, 'Compras')
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
    (9, 'Gerente general'),
    (3, 'Gerente tecnico'),
    (4, 'Jefe de taller'),
    (5, 'Almacenista'),
    (8, 'Compras')
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
    ('Administrator', 'purchase_order', 4, 4, 4, 4, 'sidebar', 'Inventario', 'inventory', 'Ordenes de compra', 530, 'compras'),   -- Administrator / administrar
    ('Administrator', 'purchase_policy', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 340, 'compras'),   -- Administrator / administrar
    ('Administrator', 'department', 4, 4, 4, 4, 'settings', 'Configuracion', 'settings', 'Departamentos', 830, 'configuracion'),   -- Administrator / administrar
    ('Administrator', 'level', 4, 4, 4, 4, 'settings', 'Configuracion', 'settings', 'Niveles', 850, 'configuracion'),   -- Administrator / administrar
    ('Administrator', 'status', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Administrator / administrar
    ('Administrator', 'subdepartment', 4, 4, 4, 4, 'settings', 'Configuracion', 'settings', 'Subdepartamentos', 840, 'configuracion'),   -- Administrator / administrar
    ('Administrator', 'theme', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Administrator / administrar
    ('Administrator', 'appointment', 4, 4, 4, 4, 'sidebar', 'CRM', 'crm', 'Calendario', 630, 'crm'),   -- Administrator / administrar
    ('Administrator', 'customer_contact', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- Administrator / administrar
    ('Administrator', 'customer_supplier', 4, 4, 4, 4, 'sidebar', 'CRM', 'crm', 'Clientes y proveedores', 620, 'crm'),   -- Administrator / administrar
    ('Administrator', 'nm_survey_user', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- Administrator / administrar
    ('Administrator', 'product_sale_config', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- Administrator / administrar
    ('Administrator', 'public_api_key', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- Administrator / administrar
    ('Administrator', 'survey_multiple_answer', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- Administrator / administrar
    ('Administrator', 'survey_question', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- Administrator / administrar
    ('Administrator', 'document', 4, 4, 4, 4, 'sidebar', 'Documentos', 'file-text', 'Documentos', 660, 'documentos'),   -- Administrator / administrar
    ('Administrator', 'document_category', 4, 4, 4, 4, 'sidebar', 'Documentos', 'file-text', 'Categorias de documento', 670, 'documentos'),   -- Administrator / administrar
    ('Administrator', 'document_relation', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 740, 'documentos'),   -- Administrator / administrar
    ('Administrator', 'document_version', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 740, 'documentos'),   -- Administrator / administrar
    ('Administrator', 'bank', 4, 4, 4, 4, 'sidebar', 'Facturacion', 'billing', 'Bancos', 140, 'facturacion'),   -- Administrator / administrar
    ('Administrator', 'bank_account', 4, 4, 4, 4, 'sidebar', 'Facturacion', 'billing', 'Cuentas bancarias', 150, 'facturacion'),   -- Administrator / administrar
    ('Administrator', 'fiscal_account', 4, 4, 4, 4, 'sidebar', 'Facturacion', 'billing', 'Cuentas fiscales', 130, 'facturacion'),   -- Administrator / administrar
    ('Administrator', 'fiscal_record', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 190, 'facturacion'),   -- Administrator / administrar
    ('Administrator', 'fiscal_stamp', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 190, 'facturacion'),   -- Administrator / administrar
    ('Administrator', 'invoice', 4, 4, 4, 4, 'sidebar', 'Facturacion', 'billing', 'Facturas', 110, 'facturacion'),   -- Administrator / administrar
    ('Administrator', 'invoice_material_service', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 190, 'facturacion'),   -- Administrator / administrar
    ('Administrator', 'service', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 190, 'facturacion'),   -- Administrator / administrar
    ('Administrator', 'ticket', 4, 4, 4, 4, 'sidebar', 'Facturacion', 'billing', 'Tickets', 160, 'facturacion'),   -- Administrator / administrar
    ('Administrator', 'brand', 4, 4, 4, 4, 'sidebar', 'Inventario', 'inventory', 'Marcas', 214, 'inventario'),   -- Administrator / administrar
    ('Administrator', 'inventory_status', 4, 4, 4, 4, 'sidebar', 'Inventario', 'inventory', 'Estado de inventario', 270, 'inventario'),   -- Administrator / administrar
    ('Administrator', 'location', 4, 4, 4, 4, 'sidebar', 'Inventario', 'inventory', 'Ubicaciones', 220, 'inventario'),   -- Administrator / administrar
    ('Administrator', 'location_type', 4, 4, 4, 4, 'sidebar', 'Inventario', 'inventory', 'Tipos de ubicacion', 230, 'inventario'),   -- Administrator / administrar
    ('Administrator', 'material', 4, 4, 4, 4, 'sidebar', 'Inventario', 'inventory', 'Materiales', 240, 'inventario'),   -- Administrator / administrar
    ('Administrator', 'material_attribute', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Administrator / administrar
    ('Administrator', 'material_component', 4, 4, 4, 4, 'sidebar', 'Inventario', 'inventory', 'Componentes', 260, 'inventario'),   -- Administrator / administrar
    ('Administrator', 'movement', 4, 4, 4, 4, 'sidebar', 'Inventario', 'inventory', 'Movimientos', 250, 'inventario'),   -- Administrator / administrar
    ('Administrator', 'product', 4, 4, 4, 4, 'sidebar', 'Inventario', 'inventory', 'Productos', 210, 'inventario'),   -- Administrator / administrar
    ('Administrator', 'product_family', 4, 4, 4, 4, 'sidebar', 'Inventario', 'inventory', 'Familias de producto', 212, 'inventario'),   -- Administrator / administrar
    ('Administrator', 'unit', 4, 4, 4, 4, 'sidebar', 'Inventario', 'inventory', 'Unidades', 216, 'inventario'),   -- Administrator / administrar
    ('Administrator', 'kpi_dashboard', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 840, 'kpis'),   -- Administrator / administrar
    ('Administrator', 'kpi_dashboard_widget', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 840, 'kpis'),   -- Administrator / administrar
    ('Administrator', 'kpi_definition', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 840, 'kpis'),   -- Administrator / administrar
    ('Administrator', 'nm_permission_kpi', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 840, 'kpis'),   -- Administrator / administrar
    ('Administrator', 'laboratory_equipment', 4, 4, 4, 4, 'sidebar', 'Laboratorio', 'flask-conical', 'Equipos', 680, 'laboratorio'),   -- Administrator / administrar
    ('Administrator', 'laboratory_service_order', 4, 4, 4, 4, 'sidebar', 'Laboratorio', 'flask-conical', 'Ordenes de servicio', 670, 'laboratorio'),   -- Administrator / administrar
    ('Administrator', 'laboratory_service_order_status_history', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 750, 'laboratorio'),   -- Administrator / administrar
    ('Administrator', 'logistics_address', 4, 4, 4, 4, 'sidebar', 'Logistica', 'logistics', 'Direcciones', 412, 'logistica'),   -- Administrator / administrar
    ('Administrator', 'logistics_branch', 4, 4, 4, 4, 'sidebar', 'Logistica', 'logistics', 'Sucursales', 410, 'logistica'),   -- Administrator / administrar
    ('Administrator', 'logistics_contact', 4, 4, 4, 4, 'sidebar', 'Logistica', 'logistics', 'Contactos', 414, 'logistica'),   -- Administrator / administrar
    ('Administrator', 'logistics_contract', 4, 4, 4, 4, 'sidebar', 'Logistica', 'logistics', 'Contratos', 416, 'logistica'),   -- Administrator / administrar
    ('Administrator', 'logistics_evidence', 4, 4, 4, 4, 'sidebar', 'Logistica', 'logistics', 'Evidencias', 446, 'logistica'),   -- Administrator / administrar
    ('Administrator', 'logistics_file', 4, 4, 4, 4, 'sidebar', 'Logistica', 'logistics', 'Expedientes', 462, 'logistica'),   -- Administrator / administrar
    ('Administrator', 'logistics_incident', 4, 4, 4, 4, 'sidebar', 'Logistica', 'logistics', 'Incidencias', 448, 'logistica'),   -- Administrator / administrar
    ('Administrator', 'logistics_inventory', 4, 4, 4, 4, 'sidebar', 'Logistica', 'logistics', 'Inventario', 436, 'logistica'),   -- Administrator / administrar
    ('Administrator', 'logistics_location', 4, 4, 4, 4, 'sidebar', 'Logistica', 'logistics', 'Ubicaciones', 432, 'logistica'),   -- Administrator / administrar
    ('Administrator', 'logistics_maintenance', 4, 4, 4, 4, 'sidebar', 'Logistica', 'logistics', 'Mantenimientos', 456, 'logistica'),   -- Administrator / administrar
    ('Administrator', 'logistics_operator', 4, 4, 4, 4, 'sidebar', 'Logistica', 'logistics', 'Operadores', 454, 'logistica'),   -- Administrator / administrar
    ('Administrator', 'logistics_quotation', 4, 4, 4, 4, 'sidebar', 'Logistica', 'logistics', 'Cotizaciones', 420, 'logistica'),   -- Administrator / administrar
    ('Administrator', 'logistics_rack', 4, 4, 4, 4, 'sidebar', 'Logistica', 'logistics', 'Racks', 434, 'logistica'),   -- Administrator / administrar
    ('Administrator', 'logistics_rate', 4, 4, 4, 4, 'sidebar', 'Logistica', 'logistics', 'Tarifas', 418, 'logistica'),   -- Administrator / administrar
    ('Administrator', 'logistics_receivable', 4, 4, 4, 4, 'sidebar', 'Logistica', 'logistics', 'Cuentas por cobrar', 460, 'logistica'),   -- Administrator / administrar
    ('Administrator', 'logistics_service_request', 4, 4, 4, 4, 'sidebar', 'Logistica', 'logistics', 'Solicitudes de servicio', 440, 'logistica'),   -- Administrator / administrar
    ('Administrator', 'logistics_shipment', 4, 4, 4, 4, 'sidebar', 'Logistica', 'logistics', 'Embarques', 444, 'logistica'),   -- Administrator / administrar
    ('Administrator', 'logistics_trailer', 4, 4, 4, 4, 'sidebar', 'Logistica', 'logistics', 'Remolques', 452, 'logistica'),   -- Administrator / administrar
    ('Administrator', 'logistics_trip', 4, 4, 4, 4, 'sidebar', 'Logistica', 'logistics', 'Viajes', 442, 'logistica'),   -- Administrator / administrar
    ('Administrator', 'logistics_unit', 4, 4, 4, 4, 'sidebar', 'Logistica', 'logistics', 'Unidades', 450, 'logistica'),   -- Administrator / administrar
    ('Administrator', 'logistics_warehouse', 4, 4, 4, 4, 'sidebar', 'Logistica', 'logistics', 'Almacenes', 430, 'logistica'),   -- Administrator / administrar
    ('Administrator', 'incident', 4, 4, 4, 4, 'sidebar', 'Operaciones', 'operations', 'Incidencias', 330, 'operaciones'),   -- Administrator / administrar
    ('Administrator', 'incident_detail', 4, 4, 4, 4, 'sidebar', 'Operaciones', 'operations', 'Subtipos de incidencia', 334, 'operaciones'),   -- Administrator / administrar
    ('Administrator', 'incident_type', 4, 4, 4, 4, 'sidebar', 'Operaciones', 'operations', 'Tipos de incidencia', 332, 'operaciones'),   -- Administrator / administrar
    ('Administrator', 'nm_incident_product', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Administrator / administrar
    ('Administrator', 'nm_template_task', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Administrator / administrar
    ('Administrator', 'proyect', 4, 4, 4, 4, 'sidebar', 'Operaciones', 'operations', 'Proyectos', 310, 'operaciones'),   -- Administrator / administrar
    ('Administrator', 'proyect_material_need', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Administrator / administrar
    ('Administrator', 'task', 4, 4, 4, 4, 'sidebar', 'Operaciones', 'operations', 'Tareas', 320, 'operaciones'),   -- Administrator / administrar
    ('Administrator', 'task_note', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Administrator / administrar
    ('Administrator', 'task_type', 4, 4, 4, 4, 'sidebar', 'Operaciones', 'operations', 'Tipos de tarea', 342, 'operaciones'),   -- Administrator / administrar
    ('Administrator', 'template', 4, 4, 4, 4, 'sidebar', 'Operaciones', 'operations', 'Plantillas de tarea', 340, 'operaciones'),   -- Administrator / administrar
    ('Administrator', 'attendance_employee_link', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 790, 'rh'),   -- Administrator / administrar
    ('Administrator', 'attendance_record', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 790, 'rh'),   -- Administrator / administrar
    ('Administrator', 'employee_leave', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 790, 'rh'),   -- Administrator / administrar
    ('Administrator', 'employee_schedule', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 790, 'rh'),   -- Administrator / administrar
    ('Administrator', 'payroll_concept', 4, 4, 4, 4, 'sidebar', 'Recursos humanos', 'hr', 'Conceptos', 720, 'rh'),   -- Administrator / administrar
    ('Administrator', 'payroll_detail', 4, 4, 4, 4, 'sidebar', 'Recursos humanos', 'hr', 'Detalle', 740, 'rh'),   -- Administrator / administrar
    ('Administrator', 'payroll_holiday', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 790, 'rh'),   -- Administrator / administrar
    ('Administrator', 'payroll_isr_bracket', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 790, 'rh'),   -- Administrator / administrar
    ('Administrator', 'payroll_movement', 4, 4, 4, 4, 'sidebar', 'Recursos humanos', 'hr', 'Movimientos', 730, 'rh'),   -- Administrator / administrar
    ('Administrator', 'payroll_parameter', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 790, 'rh'),   -- Administrator / administrar
    ('Administrator', 'payroll_period', 4, 4, 4, 4, 'sidebar', 'Recursos humanos', 'hr', 'Periodos de nomina', 710, 'rh'),   -- Administrator / administrar
    ('Administrator', 'work_schedule', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 790, 'rh'),   -- Administrator / administrar
    ('Administrator', 'work_schedule_day', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 790, 'rh'),   -- Administrator / administrar
    ('Administrator', 'entity_permission', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 990, 'seguridad'),   -- Administrator / administrar
    ('Administrator', 'field', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 990, 'seguridad'),   -- Administrator / administrar
    ('Administrator', 'nm_field_permission', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 990, 'seguridad'),   -- Administrator / administrar
    ('Administrator', 'nm_team_user', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 990, 'seguridad'),   -- Administrator / administrar
    ('Administrator', 'permission', 4, 4, 4, 4, 'settings', 'Configuracion', 'settings', 'Perfiles', 920, 'seguridad'),   -- Administrator / administrar
    ('Administrator', 'team', 4, 4, 4, 4, 'settings', 'Configuracion', 'settings', 'Equipos', 960, 'seguridad'),   -- Administrator / administrar
    ('Administrator', 'user', 4, 4, 4, 4, 'settings', 'Configuracion', 'settings', 'Usuarios', 910, 'seguridad'),   -- Administrator / administrar
    ('Administrator', 'daily_activity_log', 4, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Bitacora diaria de taller', 390, 'operaciones'),   -- Administrator / capturar
    ('Administrator', 'incident_supervision', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Administrator / consultar
    ('Administrator', 'inventory_adjustment', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Administrator / consultar
    ('Administrator', 'kronos_device', 0, 4, 0, 0, 'settings', 'Recursos humanos', 'hr', 'Conexion al dispositivo Kronos', 790, 'rh'),   -- Administrator / consultar
    ('Administrator', 'multiemisor_csd', 4, 4, 4, 4, 'sidebar', 'Facturacion', 'billing', 'Multiemisor y CSD', 190, 'multiemisor_csd'),   -- Administrator / administrar
    ('Administrator', 'pos_admin', 4, 4, 4, 4, 'sidebar', 'Punto de venta', 'pos', 'Admin del punto de venta', 640, 'pos'),   -- Administrator / administrar
    ('Administrator', 'pos_terminal', 4, 4, 4, 0, 'sidebar', 'Punto de venta', 'pos', 'Caja del punto de venta', 640, 'pos'),   -- Administrator / capturar
    ('Administrator', 'project_authorization', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Administrator / consultar
    ('Administrator', 'project_execution', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Administrator / consultar
    ('Administrator', 'project_oversight', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Administrator / consultar
    ('Administrator', 'project_supply', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Administrator / consultar
    ('Administrator', 'purchase_authorize', 0, 4, 4, 0, 'hidden', NULL, NULL, NULL, 340, 'compras'),   -- Administrator / editar
    ('Administrator', 'purchase_planning', 0, 4, 4, 0, 'sidebar', 'Inventario', 'inventory', 'Por comprar', 290, 'inventario'),   -- Administrator / editar
    ('Administrator', 'purchase_receive', 0, 4, 4, 0, 'hidden', NULL, NULL, NULL, 340, 'compras'),   -- Administrator / editar
    ('Administrator', 'restaurant_admin', 4, 4, 4, 4, 'sidebar', 'Restaurante', 'restaurant', 'Admin del restaurante', 590, 'restaurante'),   -- Administrator / administrar
    ('Administrator', 'restaurant_cashier', 4, 4, 4, 0, 'sidebar', 'Restaurante', 'restaurant', 'Caja', 590, 'restaurante'),   -- Administrator / capturar
    ('Administrator', 'restaurant_kitchen', 0, 4, 4, 0, 'sidebar', 'Restaurante', 'restaurant', 'Cocina', 590, 'restaurante'),   -- Administrator / editar
    ('Administrator', 'restaurant_waiter', 4, 4, 4, 0, 'sidebar', 'Restaurante', 'restaurant', 'Meseros', 590, 'restaurante'),   -- Administrator / capturar
    ('Administrator', 'warehouse_prevoucher', 4, 4, 4, 0, 'sidebar', 'Inventario', 'inventory', 'Prevales de material', 290, 'inventario'),   -- Administrator / capturar
    ('Administrator', 'warehouse_voucher_confirm', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Administrator / consultar
    ('Supervisor', 'department', 0, 4, 0, 0, 'settings', 'Configuracion', 'settings', 'Departamentos', 830, 'configuracion'),   -- Supervisor / consultar
    ('Supervisor', 'level', 0, 4, 0, 0, 'settings', 'Configuracion', 'settings', 'Niveles', 850, 'configuracion'),   -- Supervisor / consultar
    ('Supervisor', 'status', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Supervisor / consultar
    ('Supervisor', 'subdepartment', 0, 4, 0, 0, 'settings', 'Configuracion', 'settings', 'Subdepartamentos', 840, 'configuracion'),   -- Supervisor / consultar
    ('Supervisor', 'theme', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Supervisor / consultar
    ('Supervisor', 'brand', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Marcas', 214, 'inventario'),   -- Supervisor / consultar
    ('Supervisor', 'inventory_status', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Estado de inventario', 270, 'inventario'),   -- Supervisor / consultar
    ('Supervisor', 'location', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Ubicaciones', 220, 'inventario'),   -- Supervisor / consultar
    ('Supervisor', 'location_type', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Tipos de ubicacion', 230, 'inventario'),   -- Supervisor / consultar
    ('Supervisor', 'material', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Materiales', 240, 'inventario'),   -- Supervisor / consultar
    ('Supervisor', 'material_attribute', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Supervisor / consultar
    ('Supervisor', 'material_component', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Componentes', 260, 'inventario'),   -- Supervisor / consultar
    ('Supervisor', 'movement', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Movimientos', 250, 'inventario'),   -- Supervisor / consultar
    ('Supervisor', 'product', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Productos', 210, 'inventario'),   -- Supervisor / consultar
    ('Supervisor', 'product_family', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Familias de producto', 212, 'inventario'),   -- Supervisor / consultar
    ('Supervisor', 'unit', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Unidades', 216, 'inventario'),   -- Supervisor / consultar
    ('Supervisor', 'incident', 0, 4, 0, 0, 'sidebar', 'Operaciones', 'operations', 'Incidencias', 330, 'operaciones'),   -- Supervisor / consultar
    ('Supervisor', 'incident_detail', 4, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Subtipos de incidencia', 334, 'operaciones'),   -- Supervisor / capturar
    ('Supervisor', 'incident_type', 4, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Tipos de incidencia', 332, 'operaciones'),   -- Supervisor / capturar
    ('Supervisor', 'nm_incident_product', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Supervisor / capturar
    ('Supervisor', 'nm_template_task', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Supervisor / capturar
    ('Supervisor', 'proyect', 4, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Proyectos', 310, 'operaciones'),   -- Supervisor / capturar
    ('Supervisor', 'proyect_material_need', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Supervisor / capturar
    ('Supervisor', 'task', 0, 4, 0, 0, 'sidebar', 'Operaciones', 'operations', 'Tareas', 320, 'operaciones'),   -- Supervisor / consultar
    ('Supervisor', 'task_note', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Supervisor / capturar
    ('Supervisor', 'task_type', 4, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Tipos de tarea', 342, 'operaciones'),   -- Supervisor / capturar
    ('Supervisor', 'template', 4, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Plantillas de tarea', 340, 'operaciones'),   -- Supervisor / capturar
    ('Supervisor', 'incident_supervision', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Supervisor / consultar
    ('Supervisor', 'warehouse_prevoucher', 4, 4, 4, 0, 'sidebar', 'Inventario', 'inventory', 'Prevales de material', 290, 'inventario'),   -- Supervisor / capturar
    ('Gerente general', 'purchase_order', 4, 4, 4, 0, 'sidebar', 'Inventario', 'inventory', 'Ordenes de compra', 530, 'compras'),   -- Gerente general / capturar
    ('Gerente general', 'purchase_policy', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 340, 'compras'),   -- Gerente general / capturar
    ('Gerente general', 'department', 0, 4, 0, 0, 'settings', 'Configuracion', 'settings', 'Departamentos', 830, 'configuracion'),   -- Gerente general / consultar
    ('Gerente general', 'level', 0, 4, 0, 0, 'settings', 'Configuracion', 'settings', 'Niveles', 850, 'configuracion'),   -- Gerente general / consultar
    ('Gerente general', 'status', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Gerente general / consultar
    ('Gerente general', 'subdepartment', 0, 4, 0, 0, 'settings', 'Configuracion', 'settings', 'Subdepartamentos', 840, 'configuracion'),   -- Gerente general / consultar
    ('Gerente general', 'theme', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Gerente general / consultar
    ('Gerente general', 'appointment', 0, 4, 0, 0, 'sidebar', 'CRM', 'crm', 'Calendario', 630, 'crm'),   -- Gerente general / consultar
    ('Gerente general', 'customer_contact', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- Gerente general / consultar
    ('Gerente general', 'customer_supplier', 0, 4, 0, 0, 'sidebar', 'CRM', 'crm', 'Clientes y proveedores', 620, 'crm'),   -- Gerente general / consultar
    ('Gerente general', 'nm_survey_user', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- Gerente general / consultar
    ('Gerente general', 'product_sale_config', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- Gerente general / consultar
    ('Gerente general', 'public_api_key', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- Gerente general / consultar
    ('Gerente general', 'survey_multiple_answer', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- Gerente general / consultar
    ('Gerente general', 'survey_question', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 690, 'crm'),   -- Gerente general / consultar
    ('Gerente general', 'bank', 0, 4, 0, 0, 'sidebar', 'Facturacion', 'billing', 'Bancos', 140, 'facturacion'),   -- Gerente general / consultar
    ('Gerente general', 'bank_account', 0, 4, 0, 0, 'sidebar', 'Facturacion', 'billing', 'Cuentas bancarias', 150, 'facturacion'),   -- Gerente general / consultar
    ('Gerente general', 'fiscal_account', 0, 4, 0, 0, 'sidebar', 'Facturacion', 'billing', 'Cuentas fiscales', 130, 'facturacion'),   -- Gerente general / consultar
    ('Gerente general', 'fiscal_record', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 190, 'facturacion'),   -- Gerente general / consultar
    ('Gerente general', 'fiscal_stamp', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 190, 'facturacion'),   -- Gerente general / consultar
    ('Gerente general', 'invoice', 0, 4, 0, 0, 'sidebar', 'Facturacion', 'billing', 'Facturas', 110, 'facturacion'),   -- Gerente general / consultar
    ('Gerente general', 'invoice_material_service', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 190, 'facturacion'),   -- Gerente general / consultar
    ('Gerente general', 'service', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 190, 'facturacion'),   -- Gerente general / consultar
    ('Gerente general', 'ticket', 0, 4, 0, 0, 'sidebar', 'Facturacion', 'billing', 'Tickets', 160, 'facturacion'),   -- Gerente general / consultar
    ('Gerente general', 'brand', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Marcas', 214, 'inventario'),   -- Gerente general / consultar
    ('Gerente general', 'inventory_status', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Estado de inventario', 270, 'inventario'),   -- Gerente general / consultar
    ('Gerente general', 'location', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Ubicaciones', 220, 'inventario'),   -- Gerente general / consultar
    ('Gerente general', 'location_type', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Tipos de ubicacion', 230, 'inventario'),   -- Gerente general / consultar
    ('Gerente general', 'material', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Materiales', 240, 'inventario'),   -- Gerente general / consultar
    ('Gerente general', 'material_attribute', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Gerente general / consultar
    ('Gerente general', 'material_component', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Componentes', 260, 'inventario'),   -- Gerente general / consultar
    ('Gerente general', 'movement', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Movimientos', 250, 'inventario'),   -- Gerente general / consultar
    ('Gerente general', 'product', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Productos', 210, 'inventario'),   -- Gerente general / consultar
    ('Gerente general', 'product_family', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Familias de producto', 212, 'inventario'),   -- Gerente general / consultar
    ('Gerente general', 'unit', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Unidades', 216, 'inventario'),   -- Gerente general / consultar
    ('Gerente general', 'logistics_address', 0, 4, 0, 0, 'sidebar', 'Logistica', 'logistics', 'Direcciones', 412, 'logistica'),   -- Gerente general / consultar
    ('Gerente general', 'logistics_branch', 0, 4, 0, 0, 'sidebar', 'Logistica', 'logistics', 'Sucursales', 410, 'logistica'),   -- Gerente general / consultar
    ('Gerente general', 'logistics_contact', 0, 4, 0, 0, 'sidebar', 'Logistica', 'logistics', 'Contactos', 414, 'logistica'),   -- Gerente general / consultar
    ('Gerente general', 'logistics_contract', 0, 4, 0, 0, 'sidebar', 'Logistica', 'logistics', 'Contratos', 416, 'logistica'),   -- Gerente general / consultar
    ('Gerente general', 'logistics_evidence', 0, 4, 0, 0, 'sidebar', 'Logistica', 'logistics', 'Evidencias', 446, 'logistica'),   -- Gerente general / consultar
    ('Gerente general', 'logistics_file', 0, 4, 0, 0, 'sidebar', 'Logistica', 'logistics', 'Expedientes', 462, 'logistica'),   -- Gerente general / consultar
    ('Gerente general', 'logistics_incident', 0, 4, 0, 0, 'sidebar', 'Logistica', 'logistics', 'Incidencias', 448, 'logistica'),   -- Gerente general / consultar
    ('Gerente general', 'logistics_inventory', 0, 4, 0, 0, 'sidebar', 'Logistica', 'logistics', 'Inventario', 436, 'logistica'),   -- Gerente general / consultar
    ('Gerente general', 'logistics_location', 0, 4, 0, 0, 'sidebar', 'Logistica', 'logistics', 'Ubicaciones', 432, 'logistica'),   -- Gerente general / consultar
    ('Gerente general', 'logistics_maintenance', 0, 4, 0, 0, 'sidebar', 'Logistica', 'logistics', 'Mantenimientos', 456, 'logistica'),   -- Gerente general / consultar
    ('Gerente general', 'logistics_operator', 0, 4, 0, 0, 'sidebar', 'Logistica', 'logistics', 'Operadores', 454, 'logistica'),   -- Gerente general / consultar
    ('Gerente general', 'logistics_quotation', 0, 4, 0, 0, 'sidebar', 'Logistica', 'logistics', 'Cotizaciones', 420, 'logistica'),   -- Gerente general / consultar
    ('Gerente general', 'logistics_rack', 0, 4, 0, 0, 'sidebar', 'Logistica', 'logistics', 'Racks', 434, 'logistica'),   -- Gerente general / consultar
    ('Gerente general', 'logistics_rate', 0, 4, 0, 0, 'sidebar', 'Logistica', 'logistics', 'Tarifas', 418, 'logistica'),   -- Gerente general / consultar
    ('Gerente general', 'logistics_receivable', 0, 4, 0, 0, 'sidebar', 'Logistica', 'logistics', 'Cuentas por cobrar', 460, 'logistica'),   -- Gerente general / consultar
    ('Gerente general', 'logistics_service_request', 0, 4, 0, 0, 'sidebar', 'Logistica', 'logistics', 'Solicitudes de servicio', 440, 'logistica'),   -- Gerente general / consultar
    ('Gerente general', 'logistics_shipment', 0, 4, 0, 0, 'sidebar', 'Logistica', 'logistics', 'Embarques', 444, 'logistica'),   -- Gerente general / consultar
    ('Gerente general', 'logistics_trailer', 0, 4, 0, 0, 'sidebar', 'Logistica', 'logistics', 'Remolques', 452, 'logistica'),   -- Gerente general / consultar
    ('Gerente general', 'logistics_trip', 0, 4, 0, 0, 'sidebar', 'Logistica', 'logistics', 'Viajes', 442, 'logistica'),   -- Gerente general / consultar
    ('Gerente general', 'logistics_unit', 0, 4, 0, 0, 'sidebar', 'Logistica', 'logistics', 'Unidades', 450, 'logistica'),   -- Gerente general / consultar
    ('Gerente general', 'logistics_warehouse', 0, 4, 0, 0, 'sidebar', 'Logistica', 'logistics', 'Almacenes', 430, 'logistica'),   -- Gerente general / consultar
    ('Gerente general', 'incident', 0, 4, 0, 0, 'sidebar', 'Operaciones', 'operations', 'Incidencias', 330, 'operaciones'),   -- Gerente general / consultar
    ('Gerente general', 'incident_detail', 0, 4, 0, 0, 'sidebar', 'Operaciones', 'operations', 'Subtipos de incidencia', 334, 'operaciones'),   -- Gerente general / consultar
    ('Gerente general', 'incident_type', 0, 4, 0, 0, 'sidebar', 'Operaciones', 'operations', 'Tipos de incidencia', 332, 'operaciones'),   -- Gerente general / consultar
    ('Gerente general', 'nm_incident_product', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Gerente general / consultar
    ('Gerente general', 'nm_template_task', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Gerente general / consultar
    ('Gerente general', 'proyect', 0, 4, 0, 0, 'sidebar', 'Operaciones', 'operations', 'Proyectos', 310, 'operaciones'),   -- Gerente general / consultar
    ('Gerente general', 'proyect_material_need', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Gerente general / consultar
    ('Gerente general', 'task', 0, 4, 0, 0, 'sidebar', 'Operaciones', 'operations', 'Tareas', 320, 'operaciones'),   -- Gerente general / consultar
    ('Gerente general', 'task_note', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Gerente general / consultar
    ('Gerente general', 'task_type', 0, 4, 0, 0, 'sidebar', 'Operaciones', 'operations', 'Tipos de tarea', 342, 'operaciones'),   -- Gerente general / consultar
    ('Gerente general', 'template', 0, 4, 0, 0, 'sidebar', 'Operaciones', 'operations', 'Plantillas de tarea', 340, 'operaciones'),   -- Gerente general / consultar
    ('Gerente general', 'attendance_employee_link', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 790, 'rh'),   -- Gerente general / consultar
    ('Gerente general', 'attendance_record', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 790, 'rh'),   -- Gerente general / consultar
    ('Gerente general', 'employee_leave', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 790, 'rh'),   -- Gerente general / consultar
    ('Gerente general', 'employee_schedule', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 790, 'rh'),   -- Gerente general / consultar
    ('Gerente general', 'payroll_concept', 0, 4, 0, 0, 'sidebar', 'Recursos humanos', 'hr', 'Conceptos', 720, 'rh'),   -- Gerente general / consultar
    ('Gerente general', 'payroll_detail', 0, 4, 0, 0, 'sidebar', 'Recursos humanos', 'hr', 'Detalle', 740, 'rh'),   -- Gerente general / consultar
    ('Gerente general', 'payroll_holiday', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 790, 'rh'),   -- Gerente general / consultar
    ('Gerente general', 'payroll_isr_bracket', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 790, 'rh'),   -- Gerente general / consultar
    ('Gerente general', 'payroll_movement', 0, 4, 0, 0, 'sidebar', 'Recursos humanos', 'hr', 'Movimientos', 730, 'rh'),   -- Gerente general / consultar
    ('Gerente general', 'payroll_parameter', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 790, 'rh'),   -- Gerente general / consultar
    ('Gerente general', 'payroll_period', 0, 4, 0, 0, 'sidebar', 'Recursos humanos', 'hr', 'Periodos de nomina', 710, 'rh'),   -- Gerente general / consultar
    ('Gerente general', 'work_schedule', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 790, 'rh'),   -- Gerente general / consultar
    ('Gerente general', 'work_schedule_day', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 790, 'rh'),   -- Gerente general / consultar
    ('Gerente general', 'incident_supervision', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Gerente general / consultar
    ('Gerente general', 'project_oversight', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Gerente general / consultar
    ('Gerente general', 'purchase_authorize', 0, 4, 4, 0, 'hidden', NULL, NULL, NULL, 340, 'compras'),   -- Gerente general / editar
    ('Gerente tecnico', 'purchase_order', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Ordenes de compra', 530, 'compras'),   -- Gerente tecnico / consultar
    ('Gerente tecnico', 'purchase_policy', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 340, 'compras'),   -- Gerente tecnico / consultar
    ('Gerente tecnico', 'department', 0, 4, 0, 0, 'settings', 'Configuracion', 'settings', 'Departamentos', 830, 'configuracion'),   -- Gerente tecnico / consultar
    ('Gerente tecnico', 'level', 0, 4, 0, 0, 'settings', 'Configuracion', 'settings', 'Niveles', 850, 'configuracion'),   -- Gerente tecnico / consultar
    ('Gerente tecnico', 'status', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Gerente tecnico / consultar
    ('Gerente tecnico', 'subdepartment', 0, 4, 0, 0, 'settings', 'Configuracion', 'settings', 'Subdepartamentos', 840, 'configuracion'),   -- Gerente tecnico / consultar
    ('Gerente tecnico', 'theme', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Gerente tecnico / consultar
    ('Gerente tecnico', 'brand', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Marcas', 214, 'inventario'),   -- Gerente tecnico / consultar
    ('Gerente tecnico', 'inventory_status', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Estado de inventario', 270, 'inventario'),   -- Gerente tecnico / consultar
    ('Gerente tecnico', 'location', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Ubicaciones', 220, 'inventario'),   -- Gerente tecnico / consultar
    ('Gerente tecnico', 'location_type', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Tipos de ubicacion', 230, 'inventario'),   -- Gerente tecnico / consultar
    ('Gerente tecnico', 'material', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Materiales', 240, 'inventario'),   -- Gerente tecnico / consultar
    ('Gerente tecnico', 'material_attribute', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Gerente tecnico / consultar
    ('Gerente tecnico', 'material_component', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Componentes', 260, 'inventario'),   -- Gerente tecnico / consultar
    ('Gerente tecnico', 'movement', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Movimientos', 250, 'inventario'),   -- Gerente tecnico / consultar
    ('Gerente tecnico', 'product', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Productos', 210, 'inventario'),   -- Gerente tecnico / consultar
    ('Gerente tecnico', 'product_family', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Familias de producto', 212, 'inventario'),   -- Gerente tecnico / consultar
    ('Gerente tecnico', 'unit', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Unidades', 216, 'inventario'),   -- Gerente tecnico / consultar
    ('Gerente tecnico', 'incident', 0, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Incidencias', 330, 'operaciones'),   -- Gerente tecnico / editar
    ('Gerente tecnico', 'incident_detail', 0, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Subtipos de incidencia', 334, 'operaciones'),   -- Gerente tecnico / editar
    ('Gerente tecnico', 'incident_type', 0, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Tipos de incidencia', 332, 'operaciones'),   -- Gerente tecnico / editar
    ('Gerente tecnico', 'nm_incident_product', 0, 4, 4, 0, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Gerente tecnico / editar
    ('Gerente tecnico', 'nm_template_task', 0, 4, 4, 0, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Gerente tecnico / editar
    ('Gerente tecnico', 'proyect', 0, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Proyectos', 310, 'operaciones'),   -- Gerente tecnico / editar
    ('Gerente tecnico', 'proyect_material_need', 0, 4, 4, 0, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Gerente tecnico / editar
    ('Gerente tecnico', 'task', 0, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Tareas', 320, 'operaciones'),   -- Gerente tecnico / editar
    ('Gerente tecnico', 'task_note', 0, 4, 4, 0, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Gerente tecnico / editar
    ('Gerente tecnico', 'task_type', 0, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Tipos de tarea', 342, 'operaciones'),   -- Gerente tecnico / editar
    ('Gerente tecnico', 'template', 0, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Plantillas de tarea', 340, 'operaciones'),   -- Gerente tecnico / editar
    ('Gerente tecnico', 'incident_supervision', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Gerente tecnico / consultar
    ('Gerente tecnico', 'project_authorization', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Gerente tecnico / consultar
    ('Gerente tecnico', 'warehouse_prevoucher', 4, 4, 4, 0, 'sidebar', 'Inventario', 'inventory', 'Prevales de material', 290, 'inventario'),   -- Gerente tecnico / capturar
    ('Jefe de taller', 'department', 0, 4, 0, 0, 'settings', 'Configuracion', 'settings', 'Departamentos', 830, 'configuracion'),   -- Jefe de taller / consultar
    ('Jefe de taller', 'level', 0, 4, 0, 0, 'settings', 'Configuracion', 'settings', 'Niveles', 850, 'configuracion'),   -- Jefe de taller / consultar
    ('Jefe de taller', 'status', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Jefe de taller / consultar
    ('Jefe de taller', 'subdepartment', 0, 4, 0, 0, 'settings', 'Configuracion', 'settings', 'Subdepartamentos', 840, 'configuracion'),   -- Jefe de taller / consultar
    ('Jefe de taller', 'theme', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Jefe de taller / consultar
    ('Jefe de taller', 'brand', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Marcas', 214, 'inventario'),   -- Jefe de taller / consultar
    ('Jefe de taller', 'inventory_status', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Estado de inventario', 270, 'inventario'),   -- Jefe de taller / consultar
    ('Jefe de taller', 'location', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Ubicaciones', 220, 'inventario'),   -- Jefe de taller / consultar
    ('Jefe de taller', 'location_type', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Tipos de ubicacion', 230, 'inventario'),   -- Jefe de taller / consultar
    ('Jefe de taller', 'material', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Materiales', 240, 'inventario'),   -- Jefe de taller / consultar
    ('Jefe de taller', 'material_attribute', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Jefe de taller / consultar
    ('Jefe de taller', 'material_component', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Componentes', 260, 'inventario'),   -- Jefe de taller / consultar
    ('Jefe de taller', 'movement', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Movimientos', 250, 'inventario'),   -- Jefe de taller / consultar
    ('Jefe de taller', 'product', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Productos', 210, 'inventario'),   -- Jefe de taller / consultar
    ('Jefe de taller', 'product_family', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Familias de producto', 212, 'inventario'),   -- Jefe de taller / consultar
    ('Jefe de taller', 'unit', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Unidades', 216, 'inventario'),   -- Jefe de taller / consultar
    ('Jefe de taller', 'incident', 4, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Incidencias', 330, 'operaciones'),   -- Jefe de taller / capturar
    ('Jefe de taller', 'incident_detail', 4, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Subtipos de incidencia', 334, 'operaciones'),   -- Jefe de taller / capturar
    ('Jefe de taller', 'incident_type', 4, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Tipos de incidencia', 332, 'operaciones'),   -- Jefe de taller / capturar
    ('Jefe de taller', 'nm_incident_product', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Jefe de taller / capturar
    ('Jefe de taller', 'nm_template_task', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Jefe de taller / capturar
    ('Jefe de taller', 'proyect', 4, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Proyectos', 310, 'operaciones'),   -- Jefe de taller / capturar
    ('Jefe de taller', 'proyect_material_need', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Jefe de taller / capturar
    ('Jefe de taller', 'task', 4, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Tareas', 320, 'operaciones'),   -- Jefe de taller / capturar
    ('Jefe de taller', 'task_note', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Jefe de taller / capturar
    ('Jefe de taller', 'task_type', 4, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Tipos de tarea', 342, 'operaciones'),   -- Jefe de taller / capturar
    ('Jefe de taller', 'template', 4, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Plantillas de tarea', 340, 'operaciones'),   -- Jefe de taller / capturar
    ('Jefe de taller', 'daily_activity_log', 4, 4, 4, 0, 'sidebar', 'Operaciones', 'operations', 'Bitacora diaria de taller', 390, 'operaciones'),   -- Jefe de taller / capturar
    ('Jefe de taller', 'incident_supervision', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Jefe de taller / consultar
    ('Jefe de taller', 'project_execution', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Jefe de taller / consultar
    ('Almacenista', 'purchase_order', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Ordenes de compra', 530, 'compras'),   -- Almacenista / consultar
    ('Almacenista', 'purchase_policy', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 340, 'compras'),   -- Almacenista / consultar
    ('Almacenista', 'department', 0, 4, 0, 0, 'settings', 'Configuracion', 'settings', 'Departamentos', 830, 'configuracion'),   -- Almacenista / consultar
    ('Almacenista', 'level', 0, 4, 0, 0, 'settings', 'Configuracion', 'settings', 'Niveles', 850, 'configuracion'),   -- Almacenista / consultar
    ('Almacenista', 'status', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Almacenista / consultar
    ('Almacenista', 'subdepartment', 0, 4, 0, 0, 'settings', 'Configuracion', 'settings', 'Subdepartamentos', 840, 'configuracion'),   -- Almacenista / consultar
    ('Almacenista', 'theme', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Almacenista / consultar
    ('Almacenista', 'brand', 4, 4, 4, 4, 'sidebar', 'Inventario', 'inventory', 'Marcas', 214, 'inventario'),   -- Almacenista / administrar
    ('Almacenista', 'inventory_status', 4, 4, 4, 4, 'sidebar', 'Inventario', 'inventory', 'Estado de inventario', 270, 'inventario'),   -- Almacenista / administrar
    ('Almacenista', 'location', 4, 4, 4, 4, 'sidebar', 'Inventario', 'inventory', 'Ubicaciones', 220, 'inventario'),   -- Almacenista / administrar
    ('Almacenista', 'location_type', 4, 4, 4, 4, 'sidebar', 'Inventario', 'inventory', 'Tipos de ubicacion', 230, 'inventario'),   -- Almacenista / administrar
    ('Almacenista', 'material', 4, 4, 4, 4, 'sidebar', 'Inventario', 'inventory', 'Materiales', 240, 'inventario'),   -- Almacenista / administrar
    ('Almacenista', 'material_attribute', 4, 4, 4, 4, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Almacenista / administrar
    ('Almacenista', 'material_component', 4, 4, 4, 4, 'sidebar', 'Inventario', 'inventory', 'Componentes', 260, 'inventario'),   -- Almacenista / administrar
    ('Almacenista', 'movement', 4, 4, 4, 4, 'sidebar', 'Inventario', 'inventory', 'Movimientos', 250, 'inventario'),   -- Almacenista / administrar
    ('Almacenista', 'product', 4, 4, 4, 4, 'sidebar', 'Inventario', 'inventory', 'Productos', 210, 'inventario'),   -- Almacenista / administrar
    ('Almacenista', 'product_family', 4, 4, 4, 4, 'sidebar', 'Inventario', 'inventory', 'Familias de producto', 212, 'inventario'),   -- Almacenista / administrar
    ('Almacenista', 'unit', 4, 4, 4, 4, 'sidebar', 'Inventario', 'inventory', 'Unidades', 216, 'inventario'),   -- Almacenista / administrar
    ('Almacenista', 'logistics_address', 4, 4, 4, 0, 'sidebar', 'Logistica', 'logistics', 'Direcciones', 412, 'logistica'),   -- Almacenista / capturar
    ('Almacenista', 'logistics_branch', 4, 4, 4, 0, 'sidebar', 'Logistica', 'logistics', 'Sucursales', 410, 'logistica'),   -- Almacenista / capturar
    ('Almacenista', 'logistics_contact', 4, 4, 4, 0, 'sidebar', 'Logistica', 'logistics', 'Contactos', 414, 'logistica'),   -- Almacenista / capturar
    ('Almacenista', 'logistics_contract', 4, 4, 4, 0, 'sidebar', 'Logistica', 'logistics', 'Contratos', 416, 'logistica'),   -- Almacenista / capturar
    ('Almacenista', 'logistics_evidence', 4, 4, 4, 0, 'sidebar', 'Logistica', 'logistics', 'Evidencias', 446, 'logistica'),   -- Almacenista / capturar
    ('Almacenista', 'logistics_file', 4, 4, 4, 0, 'sidebar', 'Logistica', 'logistics', 'Expedientes', 462, 'logistica'),   -- Almacenista / capturar
    ('Almacenista', 'logistics_incident', 4, 4, 4, 0, 'sidebar', 'Logistica', 'logistics', 'Incidencias', 448, 'logistica'),   -- Almacenista / capturar
    ('Almacenista', 'logistics_inventory', 4, 4, 4, 0, 'sidebar', 'Logistica', 'logistics', 'Inventario', 436, 'logistica'),   -- Almacenista / capturar
    ('Almacenista', 'logistics_location', 4, 4, 4, 0, 'sidebar', 'Logistica', 'logistics', 'Ubicaciones', 432, 'logistica'),   -- Almacenista / capturar
    ('Almacenista', 'logistics_maintenance', 4, 4, 4, 0, 'sidebar', 'Logistica', 'logistics', 'Mantenimientos', 456, 'logistica'),   -- Almacenista / capturar
    ('Almacenista', 'logistics_operator', 4, 4, 4, 0, 'sidebar', 'Logistica', 'logistics', 'Operadores', 454, 'logistica'),   -- Almacenista / capturar
    ('Almacenista', 'logistics_quotation', 4, 4, 4, 0, 'sidebar', 'Logistica', 'logistics', 'Cotizaciones', 420, 'logistica'),   -- Almacenista / capturar
    ('Almacenista', 'logistics_rack', 4, 4, 4, 0, 'sidebar', 'Logistica', 'logistics', 'Racks', 434, 'logistica'),   -- Almacenista / capturar
    ('Almacenista', 'logistics_rate', 4, 4, 4, 0, 'sidebar', 'Logistica', 'logistics', 'Tarifas', 418, 'logistica'),   -- Almacenista / capturar
    ('Almacenista', 'logistics_receivable', 4, 4, 4, 0, 'sidebar', 'Logistica', 'logistics', 'Cuentas por cobrar', 460, 'logistica'),   -- Almacenista / capturar
    ('Almacenista', 'logistics_service_request', 4, 4, 4, 0, 'sidebar', 'Logistica', 'logistics', 'Solicitudes de servicio', 440, 'logistica'),   -- Almacenista / capturar
    ('Almacenista', 'logistics_shipment', 4, 4, 4, 0, 'sidebar', 'Logistica', 'logistics', 'Embarques', 444, 'logistica'),   -- Almacenista / capturar
    ('Almacenista', 'logistics_trailer', 4, 4, 4, 0, 'sidebar', 'Logistica', 'logistics', 'Remolques', 452, 'logistica'),   -- Almacenista / capturar
    ('Almacenista', 'logistics_trip', 4, 4, 4, 0, 'sidebar', 'Logistica', 'logistics', 'Viajes', 442, 'logistica'),   -- Almacenista / capturar
    ('Almacenista', 'logistics_unit', 4, 4, 4, 0, 'sidebar', 'Logistica', 'logistics', 'Unidades', 450, 'logistica'),   -- Almacenista / capturar
    ('Almacenista', 'logistics_warehouse', 4, 4, 4, 0, 'sidebar', 'Logistica', 'logistics', 'Almacenes', 430, 'logistica'),   -- Almacenista / capturar
    ('Almacenista', 'inventory_adjustment', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Almacenista / consultar
    ('Almacenista', 'purchase_planning', 0, 4, 4, 0, 'sidebar', 'Inventario', 'inventory', 'Por comprar', 290, 'inventario'),   -- Almacenista / editar
    ('Almacenista', 'purchase_receive', 0, 4, 4, 0, 'hidden', NULL, NULL, NULL, 340, 'compras'),   -- Almacenista / editar
    ('Almacenista', 'warehouse_voucher', 4, 4, 4, 0, 'sidebar', 'Inventario', 'inventory', 'Vales de almacen', 290, 'inventario'),   -- Almacenista / capturar
    ('Almacenista', 'warehouse_voucher_authorize', 4, 4, 4, 0, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Almacenista / capturar
    ('Almacenista', 'warehouse_voucher_confirm', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Almacenista / consultar
    ('Compras', 'purchase_order', 4, 4, 4, 0, 'sidebar', 'Inventario', 'inventory', 'Ordenes de compra', 530, 'compras'),   -- Compras / capturar
    ('Compras', 'purchase_policy', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 340, 'compras'),   -- Compras / consultar
    ('Compras', 'department', 0, 4, 0, 0, 'settings', 'Configuracion', 'settings', 'Departamentos', 830, 'configuracion'),   -- Compras / consultar
    ('Compras', 'level', 0, 4, 0, 0, 'settings', 'Configuracion', 'settings', 'Niveles', 850, 'configuracion'),   -- Compras / consultar
    ('Compras', 'status', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Compras / consultar
    ('Compras', 'subdepartment', 0, 4, 0, 0, 'settings', 'Configuracion', 'settings', 'Subdepartamentos', 840, 'configuracion'),   -- Compras / consultar
    ('Compras', 'theme', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 890, 'configuracion'),   -- Compras / consultar
    ('Compras', 'brand', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Marcas', 214, 'inventario'),   -- Compras / consultar
    ('Compras', 'inventory_status', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Estado de inventario', 270, 'inventario'),   -- Compras / consultar
    ('Compras', 'location', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Ubicaciones', 220, 'inventario'),   -- Compras / consultar
    ('Compras', 'location_type', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Tipos de ubicacion', 230, 'inventario'),   -- Compras / consultar
    ('Compras', 'material', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Materiales', 240, 'inventario'),   -- Compras / consultar
    ('Compras', 'material_attribute', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 290, 'inventario'),   -- Compras / consultar
    ('Compras', 'material_component', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Componentes', 260, 'inventario'),   -- Compras / consultar
    ('Compras', 'movement', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Movimientos', 250, 'inventario'),   -- Compras / consultar
    ('Compras', 'product', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Productos', 210, 'inventario'),   -- Compras / consultar
    ('Compras', 'product_family', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Familias de producto', 212, 'inventario'),   -- Compras / consultar
    ('Compras', 'unit', 0, 4, 0, 0, 'sidebar', 'Inventario', 'inventory', 'Unidades', 216, 'inventario'),   -- Compras / consultar
    ('Compras', 'incident', 0, 4, 0, 0, 'sidebar', 'Operaciones', 'operations', 'Incidencias', 330, 'operaciones'),   -- Compras / consultar
    ('Compras', 'incident_detail', 0, 4, 0, 0, 'sidebar', 'Operaciones', 'operations', 'Subtipos de incidencia', 334, 'operaciones'),   -- Compras / consultar
    ('Compras', 'incident_type', 0, 4, 0, 0, 'sidebar', 'Operaciones', 'operations', 'Tipos de incidencia', 332, 'operaciones'),   -- Compras / consultar
    ('Compras', 'nm_incident_product', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Compras / consultar
    ('Compras', 'nm_template_task', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Compras / consultar
    ('Compras', 'proyect', 0, 4, 0, 0, 'sidebar', 'Operaciones', 'operations', 'Proyectos', 310, 'operaciones'),   -- Compras / consultar
    ('Compras', 'proyect_material_need', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Compras / consultar
    ('Compras', 'task', 0, 4, 0, 0, 'sidebar', 'Operaciones', 'operations', 'Tareas', 320, 'operaciones'),   -- Compras / consultar
    ('Compras', 'task_note', 0, 4, 0, 0, 'hidden', NULL, NULL, NULL, 390, 'operaciones'),   -- Compras / consultar
    ('Compras', 'task_type', 0, 4, 0, 0, 'sidebar', 'Operaciones', 'operations', 'Tipos de tarea', 342, 'operaciones'),   -- Compras / consultar
    ('Compras', 'template', 0, 4, 0, 0, 'sidebar', 'Operaciones', 'operations', 'Plantillas de tarea', 340, 'operaciones'),   -- Compras / consultar
    ('Compras', 'purchase_planning', 0, 4, 4, 0, 'sidebar', 'Inventario', 'inventory', 'Por comprar', 290, 'inventario')   -- Compras / editar
) AS v (role_name, entity_name, scope_create, scope_read, scope_update, scope_delete,
        menu_location, menu_group, menu_group_icon, menu_label, menu_order, modulo_licencia);

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

INSERT INTO entity_permission (
    id_permission, entity_name, scope_create, scope_read, scope_update, scope_delete,
    menu_location, menu_group, menu_group_icon, menu_label, menu_order, created_by
)
SELECT p.id_permission, m.entity_name,
       m.scope_create, m.scope_read, m.scope_update, m.scope_delete,
       m.menu_location, m.menu_group, m.menu_group_icon, m.menu_label, m.menu_order, 1
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
   AND c.table_name NOT IN ('daily_activity_log', 'incident_supervision', 'inventory_adjustment', 'kronos_device', 'multiemisor_csd', 'pos_admin', 'pos_terminal', 'project_authorization', 'project_execution', 'project_oversight', 'project_supply', 'purchase_authorize', 'purchase_planning', 'purchase_receive', 'restaurant_admin', 'restaurant_cashier', 'restaurant_kitchen', 'restaurant_waiter', 'warehouse_prevoucher', 'warehouse_voucher', 'warehouse_voucher_authorize', 'warehouse_voucher_confirm')
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
   AND f.table_name NOT IN ('daily_activity_log', 'incident_supervision', 'inventory_adjustment', 'kronos_device', 'multiemisor_csd', 'pos_admin', 'pos_terminal', 'project_authorization', 'project_execution', 'project_oversight', 'project_supply', 'purchase_authorize', 'purchase_planning', 'purchase_receive', 'restaurant_admin', 'restaurant_cashier', 'restaurant_kitchen', 'restaurant_waiter', 'warehouse_prevoucher', 'warehouse_voucher', 'warehouse_voucher_authorize', 'warehouse_voucher_confirm')
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
-- El campo se ve por omision si la entidad tiene algo de lectura (scope_read
-- != 0, bit 2), y se puede escribir si la entidad tiene alta o actualizacion
-- (scope_create/scope_update != 0, bits 1 y 4 -- los mismos que
-- FIELD_WRITE_BITS consulta en app/routes/task.py). Antes esta derivacion
-- solo prendia el bit de lectura: un rol con alta/actualizacion a nivel de
-- ENTIDAD (entity_permission.scope_create/update) se quedaba sin ningun
-- campo escribible a nivel de CAMPO (nm_field_permission), porque esta
-- consulta nunca encendia los bits 1/4 -- ni siquiera para una fila nueva.
-- El sintoma real: el formulario generico "guardaba" sin error visible, pero
-- el payload llegaba vacio (cada campo se filtraba por no-escribible) y la
-- ruta fallaba con 404 al no encontrar el proyecto de una tarea sin
-- `id_proyect`. GREATEST(..., 1) preserva el viejo piso de '1' cuando la
-- entidad no tiene ningun permiso (el Enum no admite '0').
SELECT f.id_field, ep.id_permission,
       GREATEST(
         (CASE WHEN ep.scope_read > 0 THEN 2 ELSE 0 END)
         + (CASE WHEN ep.scope_create > 0 THEN 1 ELSE 0 END)
         + (CASE WHEN ep.scope_update > 0 THEN 4 ELSE 0 END),
         1
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

