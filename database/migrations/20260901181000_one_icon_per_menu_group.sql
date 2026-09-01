-- Un icono por grupo de menu.
--
-- El grupo hereda el icono del primer renglon que lo crea, y "Operaciones"
-- tenia dos valores repartidos entre sus filas -`operations` en unas y
-- `briefcase-business` en otras, resto de una migracion anterior-. El resultado
-- medido: el icono del grupo cambiaba segun el rol, porque cambiaba cual de sus
-- pantallas se listaba primero. No rompe nada, pero un menu que se ve distinto
-- para cada quien es un menu que nadie puede describir a otro por telefono.
--
-- Se alinea con lo que declara `backend/app/modules/registry.py`, que es la
-- fuente de verdad de a que modulo pertenece cada entidad y con que icono se
-- pinta.

BEGIN;

UPDATE entity_permission SET menu_group_icon = 'operations', last_update_date = now()
 WHERE deletion_date IS NULL AND menu_group = 'Operaciones' AND menu_group_icon IS DISTINCT FROM 'operations';

UPDATE entity_permission SET menu_group_icon = 'settings', last_update_date = now()
 WHERE deletion_date IS NULL AND menu_group = 'Configuracion' AND menu_group_icon IS DISTINCT FROM 'settings';

UPDATE entity_permission SET menu_group_icon = 'inventory', last_update_date = now()
 WHERE deletion_date IS NULL AND menu_group = 'Inventario' AND menu_group_icon IS DISTINCT FROM 'inventory';

UPDATE entity_permission SET menu_group_icon = 'billing', last_update_date = now()
 WHERE deletion_date IS NULL AND menu_group = 'Facturacion' AND menu_group_icon IS DISTINCT FROM 'billing';

UPDATE entity_permission SET menu_group_icon = 'hr', last_update_date = now()
 WHERE deletion_date IS NULL AND menu_group = 'Recursos humanos' AND menu_group_icon IS DISTINCT FROM 'hr';

UPDATE entity_permission SET menu_group_icon = 'crm', last_update_date = now()
 WHERE deletion_date IS NULL AND menu_group = 'CRM' AND menu_group_icon IS DISTINCT FROM 'crm';

UPDATE entity_permission SET menu_group_icon = 'restaurant', last_update_date = now()
 WHERE deletion_date IS NULL AND menu_group = 'Restaurante' AND menu_group_icon IS DISTINCT FROM 'restaurant';

UPDATE entity_permission SET menu_group_icon = 'pos', last_update_date = now()
 WHERE deletion_date IS NULL AND menu_group = 'Punto de venta' AND menu_group_icon IS DISTINCT FROM 'pos';

-- Se listan las dos grafias en vez de usar LIKE. El aplicador manda el archivo
-- entero al driver, que busca marcadores de parametro en todo el texto -los
-- comentarios incluidos-, asi que un signo de porcentaje aqui tumba la
-- migracion aunque este dentro de un comentario.
UPDATE entity_permission SET menu_group_icon = 'truck', last_update_date = now()
 WHERE deletion_date IS NULL AND menu_group IN ('Logística', 'Logistica')
   AND menu_group_icon IS DISTINCT FROM 'truck';

COMMIT;
