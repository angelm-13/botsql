-- "Mis vacaciones" (`my_leaves`) para los roles que el registro no declara.
--
-- Hasta 2026-11-02 la pantalla se mostraba fija a todo usuario con sesion, sin fila
-- en el Gestor. Al volverla capacidad, la resiembra 20261102100000 la siembra a los
-- 7 roles del registro; los roles propios de cada cliente (creados desde el Gestor)
-- se quedarian sin ella al promover. Aqui se les da igual, para que nadie pierda el
-- menu de golpe: quitarla a un rol es decision del Gestor, no de una migracion.
--
-- Solo AGREGA: ON CONFLICT DO NOTHING, asi que una fila que el Gestor ya ajusto -o
-- que dio de baja- se respeta. Se reaplica en cada arranque. Si el plan del cliente
-- no trae `rh`, la resiembra no sembro ninguna fila `my_leaves` y esto no hace nada.

BEGIN;

DO $$
BEGIN
IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'entity_permission' AND column_name = 'scope_create'
) AND EXISTS (
    SELECT 1 FROM entity_permission WHERE entity_name = 'my_leaves'
) THEN
    INSERT INTO entity_permission (
        id_permission, entity_name, scope_create, scope_read, scope_update, scope_delete,
        menu_location, menu_group, menu_group_icon, menu_label, menu_order, created_by
    )
    SELECT p.id_permission, 'my_leaves', 4, 4, 4, 0,
           'sidebar', 'Recursos humanos', 'hr', 'Mis vacaciones', 790, 1
    FROM permission p
    WHERE p.deletion_date IS NULL
    ON CONFLICT (id_permission, entity_name) DO NOTHING;
END IF;
END $$;

COMMIT;
