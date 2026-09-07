-- Normalizar como se presenta el grupo Operaciones del menu.
--
-- Continuacion de 20260903110000_normalizar_orden_del_menu_inventario.sql, que
-- cerraba diciendo: "Alcance: solo el grupo Inventario. El resto del menu
-- arrastra el mismo problema y se normalizara cuando se decida, no de paso."
-- Esta es la decision para Operaciones.
--
-- Que estaba mal
-- --------------
-- Medido en la base, el mismo grupo se pintaba distinto para cada rol:
--
--     Administrator   Proyectos, Incidencias, Detalle de incidencias, Tareas,
--                     Notas de tarea, Tipos de tarea, Calendario
--     Supervisor      Calendario, Proyectos, Tareas, Notas de tarea, Tipos de
--                     tarea, Incidencias, Detalle de incidencias
--     Jefe de taller  Proyectos, Tareas, Notas de tarea, Tipos de tarea
--     Gerente         Calendario, Proyectos, Tipos de tarea
--
-- Cinco problemas distintos en esas cuatro listas:
--
--   * **dos numeraciones.** Unas filas usan 80-130 y otras 320-340, herencia de
--     que la numeracion del registro (300 + orden) llego despues. El grupo se
--     ordena por `menu_order`, asi que para Administrator las tareas salen
--     DETRAS de las incidencias -320 contra 120- y para Supervisor delante.
--     Mismo menu, dos ordenes, segun de que rol se hable.
--
--   * **dos iconos en el mismo grupo.** Unas filas dicen `operations` y otras
--     `briefcase-business`. El menu toma un icono por grupo, asi que cual gana
--     depende de que fila se lea primero. Es lo mismo que arreglo
--     20260901181000_one_icon_per_menu_group.sql para los demas grupos.
--
--   * **el calendario arrastraba el grupo.** `appointment` estaba en 75 para
--     Supervisor y Gerente y en 900 para Administrator. Como el grupo se coloca
--     por el `menu_order` mas bajo que contiene, con 75 Operaciones entero se
--     iba delante de Inventario y ademas el calendario salia por delante de
--     Proyectos, que es por donde se entra al flujo.
--
--   * **una etiqueta que nombra otra cosa.** "Detalle de incidencias" esta
--     justo debajo de "Incidencias" y se lee como su detalle, pero
--     `incident_detail.id_incident_type` apunta al TIPO, no a la incidencia: es
--     un catalogo de subtipos. Quien buscaba el detalle de una incidencia abria
--     un catalogo.
--
--   * **hijos ascendidos a hermanos.** `task_note.id_task` es NOT NULL, o sea
--     que una nota no existe sin su tarea; con entrada propia habia que abrir
--     una tercera pantalla y elegir la tarea en un desplegable para escribir
--     una nota, y la bitacora de una tarea no se leia junta en ningun sitio.
--     Se captura y se lee dentro de la tarea, en el expediente del proyecto.
--
-- Y una entidad obligatoria sin puerta: `incident_type` esta en `hidden` y sin
-- etiqueta para los tres roles que la tienen, pero
-- `incident.id_incident_type` es NOT NULL. O sea que levantar una incidencia
-- exige un tipo y no habia forma de dar uno de alta desde el menu. Es el mismo
-- fallo silencioso que tuvo `product_family` en inventario: el permiso
-- concedido, la pantalla existiendo, su ruta respondiendo, y ninguna entrada.
-- `template` estaba igual.
--
-- Que toca y que no
-- -----------------
-- Igual que la de inventario, y por la misma razon: las filas mal ordenadas YA
-- tienen etiqueta, asi que la regla habitual -nombrar solo lo que
-- `menu_label IS NULL`- las dejaria fuera y el grupo se queda asi para siempre.
-- El limite es lo que se toca:
--
--   * se normaliza la PRESENTACION -orden, etiqueta e icono-, que es lo
--     incoherente;
--   * NO se toca `control_type`, asi que nadie gana ni pierde un permiso. Quien
--     tenia acceso a `task_note` lo conserva y la ruta `/task_note` sigue
--     respondiendo; lo que cambia es que ya no hay que ir a buscarla. Y
--     `incident_type` sale al menu con el acceso que cada rol ya tenia: quien
--     solo consulta sigue consultando;
--   * `menu_location` se toca SOLO para sacar `task_note` del menu y para meter
--     al menu lo que nadie habia nombrado. Quien eligio esconder otra cosa la
--     sigue teniendo escondida.
--
-- Sobre los numeros: son los del registro (`MENU` en app/modules/registry.py),
-- que para operaciones da 300 + orden. Se escriben aqui iguales para que una
-- base migrada y una recien sembrada se lean igual; si divergen, el mismo menu
-- se presenta distinto segun de donde salio la base, que es exactamente el
-- problema que arreglo la de inventario.
--
-- Lo que esta migracion NO arregla, a proposito
-- ---------------------------------------------
-- El rol Gerente no tiene fila de `task` ni de `task_note` -no estan
-- escondidas: no existen- y si tiene "Tipos de tarea", que es un catalogo que
-- hoy nadie consume (`task` no tiene `id_task_type`; su columna `type` es un
-- Enum('personal','business')). O sea que ve el catalogo de tipos y no ve las
-- tareas. Eso es la matriz de permisos, no la presentacion del menu, y esta
-- migracion no reparte accesos: se deja anotado para decidirlo aparte.

BEGIN;

-- 1. Nombrar lo que el registro ahora nombra y la base tenia escondido.
--
--    Aqui SI se aplica la regla habitual -solo filas sin etiqueta-: una fila
--    con etiqueta la nombro alguien eligiendo donde va.
UPDATE entity_permission ep
SET menu_location = 'sidebar',
    menu_group = 'Operaciones',
    menu_group_icon = 'operations',
    menu_label = c.etiqueta,
    menu_order = c.orden,
    last_update_date = now()
FROM (VALUES
    ('incident_type', 'Tipos de incidencia', 332),
    ('template',      'Plantillas de tarea', 340)
) AS c (entidad, etiqueta, orden)
WHERE ep.entity_name = c.entidad
  AND ep.deletion_date IS NULL
  AND ep.menu_label IS NULL;

-- 2. Un orden y un icono para todo el grupo, con etiquetas que nombran lo que
--    abren.
UPDATE entity_permission ep
SET menu_label = c.etiqueta,
    menu_group_icon = 'operations',
    menu_order = c.orden,
    last_update_date = now()
FROM (VALUES
    -- Primero el proceso, de arriba abajo: el proyecto y las tareas en que se
    -- parte. `task.id_proyect` es NOT NULL, asi que este es el orden en que hay
    -- que recorrerlo, no una preferencia.
    ('proyect',         'Proyectos',              310),
    ('task',            'Tareas',                 320),
    -- Las incidencias son un proceso aparte, con su catalogo detras.
    ('incident',        'Incidencias',            330),
    ('incident_type',   'Tipos de incidencia',    332),
    ('incident_detail', 'Subtipos de incidencia', 334),
    -- Y al final los catalogos de apoyo y la agenda.
    ('template',        'Plantillas de tarea',    340),
    ('task_type',       'Tipos de tarea',         342),
    ('appointment',     'Calendario',             350)
) AS c (entidad, etiqueta, orden)
WHERE ep.entity_name = c.entidad
  AND ep.menu_group = 'Operaciones'
  AND ep.deletion_date IS NULL;

-- 3. Sacar del menu la nota de tarea, que ahora se captura dentro de la tarea.
--
--    Solo la ubicacion y el orden. La etiqueta se conserva: si alguien decide
--    devolverla al menu desde el gestor, vuelve con su nombre y no en blanco.
--    El icono si se normaliza: aunque la fila quede escondida sigue perteneciendo
--    al grupo, y 20260901181000_one_icon_per_menu_group.sql fija que un grupo
--    tenga un solo icono. Sin esto quedaban dos -`operations` y
--    `briefcase-business`- y cual gana depende de que fila se lea primero.
UPDATE entity_permission
SET menu_location = 'hidden',
    menu_group_icon = 'operations',
    menu_order = 390,
    last_update_date = now()
WHERE entity_name = 'task_note'
  AND menu_group = 'Operaciones'
  AND deletion_date IS NULL;

-- 4. Devolver el catalogo de servicios a facturacion, que es su modulo.
--
--    En la base medida `service` esta en `hidden` sin grupo, asi que esto no
--    toca nada: quien lo ponia en Operaciones era el frontend, que cuando una
--    fila no traia grupo lo adivinaba por la ruta. Se deja por las bases donde
--    si quedo escrito.
UPDATE entity_permission
SET menu_group = 'Facturacion',
    menu_group_icon = 'billing',
    menu_order = 170,
    last_update_date = now()
WHERE entity_name = 'service'
  AND menu_group = 'Operaciones'
  AND deletion_date IS NULL;

COMMIT;
