BEGIN;

UPDATE entity_permission
SET menu_label = 'Calendario',
    menu_group = 'Operaciones',
    menu_location = 'sidebar',
    menu_group_icon = 'calendar-days',
    last_update_date = CURRENT_TIMESTAMP
WHERE entity_name = 'appointment'
  AND deletion_date IS NULL;

COMMIT;