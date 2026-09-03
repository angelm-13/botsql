-- Normalizar como se presenta el grupo Inventario del menu.
--
-- Que estaba mal
-- --------------
-- El mismo grupo se pintaba distinto segun el rol. Medido en la base, tres
-- incoherencias a la vez sobre las mismas entidades:
--
--   * **dos numeraciones.** `brand` tenia orden 214 para Administrator,
--     Supervisor y Gerente, y 150 para Almacenista y Jefe de almacen. El grupo
--     se ordena por `menu_order`, asi que cada rol veia las entradas en un
--     orden distinto, y para los que mezclaban las dos numeraciones salia
--     "Movimientos, Componentes, Productos, Familias de producto...": los
--     catalogos despues de lo que se apoya en ellos.
--
--   * **dos iconos en el mismo grupo.** Unas filas decian `warehouse` y otras
--     `inventory`. El menu toma un icono por grupo, asi que cual gana depende
--     de que fila se lea primero.
--
--   * **dos etiquetas para la misma pantalla.** `location_type` decia "Tipos de
--     ubicacion" para tres roles y "Tipo de ubicacion" para dos.
--
-- Es la herencia de dos numeraciones que convivieron: una vieja de 100 a 190 y
-- la del registro, que reserva 200-299 para inventario.
--
-- Por que esta migracion SI pisa filas que el gestor pudo configurar
-- ------------------------------------------------------------------
-- Es la excepcion, pedida a proposito. Las demas migraciones solo nombran filas
-- sin etiqueta, precisamente para no revertir el trabajo de un administrador.
-- Aqui no alcanza: las filas con el orden viejo YA tienen etiqueta, asi que la
-- regla habitual las deja fuera y el grupo se queda desordenado para siempre.
--
-- El limite es lo que se toca:
--
--   * se normaliza la PRESENTACION -orden, etiqueta e icono-, que es lo que
--     estaba incoherente;
--   * NO se toca `control_type`, asi que nadie gana ni pierde un permiso;
--   * NO se toca `menu_location`, asi que quien eligio esconder una entrada la
--     sigue teniendo escondida, y quien la puso en el engrane la conserva ahi.
--
-- Con eso, lo que un administrador puede haber decidido -quien entra y donde
-- aparece- se respeta; lo que se corrige es solo en que orden se leen y con que
-- nombre, que no es una decision sino un descuido de dos numeraciones.
--
-- Alcance: solo el grupo Inventario. El resto del menu arrastra el mismo
-- problema y se normalizara cuando se decida, no de paso.

BEGIN;

UPDATE entity_permission ep
SET menu_label = c.etiqueta,
    menu_group_icon = c.icono,
    menu_order = c.orden,
    last_update_date = now()
FROM (VALUES
    -- El orden es el de captura: primero los catalogos de los que cuelga un
    -- producto, luego donde se guarda, luego lo que se le hace.
    ('product',              'Productos',            'inventory', 210),
    ('product_family',       'Familias de producto', 'inventory', 212),
    ('brand',                'Marcas',               'inventory', 214),
    ('unit',                 'Unidades',             'inventory', 216),
    ('location',             'Ubicaciones',          'inventory', 220),
    ('location_type',        'Tipos de ubicacion',   'inventory', 230),
    ('material',             'Materiales',           'inventory', 240),
    ('movement',             'Movimientos',          'inventory', 250),
    ('material_component',   'Componentes',          'inventory', 260),
    ('inventory_status',     'Estado de inventario', 'inventory', 270)
) AS c (entidad, etiqueta, icono, orden)
WHERE ep.entity_name = c.entidad
  AND ep.menu_group = 'Inventario'
  AND ep.deletion_date IS NULL;

-- La capacidad de ajustar existencias no es una pantalla y el registro no le da
-- orden, pero en la base vivia en 170, o sea delante de todo el grupo. Se
-- manda al final para que el bloque de arriba quede en su orden. La etiqueta no
-- se toca: la eligio alguien, y el registro no propone otra.
UPDATE entity_permission
SET menu_group_icon = 'inventory',
    menu_order = 280,
    last_update_date = now()
WHERE entity_name = 'inventory_adjustment'
  AND menu_group = 'Inventario'
  AND deletion_date IS NULL;

COMMIT;
