-- Logistica y el calendario, en el menu que les toca.
--
-- El hueco
-- --------
-- Las 21 pantallas de logistica existen desde que se integro tny_logistics, y
-- su migracion les escribio la etiqueta del menu a mano. Lo que nunca se hizo
-- fue declararlas en `MENU` dentro de `app/modules/registry.py`, y ahi la regla
-- es: una entidad sin etiqueta se siembra en `hidden`.
--
-- Consecuencia medida contra la base antes de este cambio: las 21 filas de
-- Administrator y las 9 de Gerente estaban en `sidebar` con etiqueta -- lo que
-- la migracion de tny_logistics escribio -- mientras el registro decia
-- `hidden` para todas. O sea que en ESTA base se ven, pero:
--
--   * una instalacion NUEVA se sembraba con el modulo entero sin menu. Las
--     rutas responden y el permiso existe, pero solo se llega escribiendo la
--     direccion a mano;
--   * las 21 etiquetas se perdian en la primera resiembra que tocara esas
--     filas, porque nada en el registro las respaldaba. Es exactamente lo que
--     ya habia pasado con la conexion al dispositivo Kronos.
--
-- Ademas, las 21 compartian `menu_order` 490 -- el valor por omision que da
-- `filas_de_permisos()` a una entidad sin entrada -- asi que el menu las
-- ordenaba alfabeticamente: "Almacenes, Contactos, Contratos, Cotizaciones,
-- Cuentas por cobrar, Direcciones..." Ahora el registro les da el orden del
-- trabajo, como ya lo tienen inventario y operaciones.
--
-- El calendario (`appointment`) tenia el mismo hueco, mas uno propio: la base
-- lo agrupaba bajo "Operaciones" cuando `appointment` pertenece a CRM, que es
-- de donde sale la cita. Con el grupo escrito a mano de un lado y el modulo
-- del otro, la pantalla aparecia en un sitio u otro segun quien resembrara.
--
-- Que hace
-- --------
-- Alinea las filas EXISTENTES con lo que el registro declara ahora. Solo toca
-- navegacion -ubicacion, grupo, icono, etiqueta y orden-: ni un bit de permiso
-- cambia aqui, asi que nadie gana ni pierde acceso. Las instalaciones nuevas ya
-- no lo necesitan: les llega bien desde la matriz generada.

BEGIN;

CREATE TEMP TABLE menu_objetivo (
    entity_name text PRIMARY KEY,
    menu_group text,
    menu_group_icon text,
    menu_label text,
    menu_order integer
);

INSERT INTO menu_objetivo VALUES
  ('logistics_branch',          'Logistica', 'logistics', 'Sucursales',              410),
  ('logistics_address',         'Logistica', 'logistics', 'Direcciones',             412),
  ('logistics_contact',         'Logistica', 'logistics', 'Contactos',               414),
  ('logistics_contract',        'Logistica', 'logistics', 'Contratos',               416),
  ('logistics_rate',            'Logistica', 'logistics', 'Tarifas',                 418),
  ('logistics_quotation',       'Logistica', 'logistics', 'Cotizaciones',            420),
  ('logistics_warehouse',       'Logistica', 'logistics', 'Almacenes',               430),
  ('logistics_location',        'Logistica', 'logistics', 'Ubicaciones',             432),
  ('logistics_rack',            'Logistica', 'logistics', 'Racks',                   434),
  ('logistics_inventory',       'Logistica', 'logistics', 'Inventario',              436),
  ('logistics_service_request', 'Logistica', 'logistics', 'Solicitudes de servicio', 440),
  ('logistics_trip',            'Logistica', 'logistics', 'Viajes',                  442),
  ('logistics_shipment',        'Logistica', 'logistics', 'Embarques',               444),
  ('logistics_evidence',        'Logistica', 'logistics', 'Evidencias',              446),
  ('logistics_incident',        'Logistica', 'logistics', 'Incidencias',             448),
  ('logistics_unit',            'Logistica', 'logistics', 'Unidades',                450),
  ('logistics_trailer',         'Logistica', 'logistics', 'Remolques',               452),
  ('logistics_operator',        'Logistica', 'logistics', 'Operadores',              454),
  ('logistics_maintenance',     'Logistica', 'logistics', 'Mantenimientos',          456),
  ('logistics_receivable',      'Logistica', 'logistics', 'Cuentas por cobrar',      460),
  ('logistics_file',            'Logistica', 'logistics', 'Expedientes',             462),
  ('appointment',               'CRM',       'crm',       'Calendario',              630);

UPDATE entity_permission ep
   SET menu_location = 'sidebar',
       menu_group = m.menu_group,
       menu_group_icon = m.menu_group_icon,
       menu_label = m.menu_label,
       menu_order = m.menu_order,
       last_update_date = now()
  FROM menu_objetivo m
 WHERE ep.entity_name = m.entity_name
   AND ep.deletion_date IS NULL
   AND (
        ep.menu_location IS DISTINCT FROM 'sidebar'
     OR ep.menu_group IS DISTINCT FROM m.menu_group
     OR ep.menu_group_icon IS DISTINCT FROM m.menu_group_icon
     OR ep.menu_label IS DISTINCT FROM m.menu_label
     OR ep.menu_order IS DISTINCT FROM m.menu_order
   );

DROP TABLE menu_objetivo;

COMMIT;
