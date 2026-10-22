-- El Gerente Comercial (revision) lee los vales y el almacen sin poder levantarlos
-- ni autorizarlos: una fila `warehouse_voucher` con solo `scope_read`. No va en el
-- registro porque los bits de una capacidad son uno solo para todo el que la
-- tenga (ver el comentario de ROLES); mismo trato que tuvo Gerente en
-- 20260921120000.
--
-- Solo AGREGA: ON CONFLICT DO NOTHING, asi que si el Gestor ya ajusto la fila, se
-- respeta. Se reaplica en cada arranque.

BEGIN;

DO $$
BEGIN
IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'entity_permission' AND column_name = 'scope_create'
) THEN
    INSERT INTO entity_permission (
        id_permission, entity_name, scope_create, scope_read, scope_update, scope_delete,
        menu_location, menu_group, menu_group_icon, menu_label, menu_order, created_by, creation_date, last_update_date
    )
    SELECT general.id_permission, 'warehouse_voucher', 0, 4, 0, 0,
           COALESCE(referencia.menu_location, 'hidden'), referencia.menu_group,
           referencia.menu_group_icon, referencia.menu_label,
           COALESCE(referencia.menu_order, 299), 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
    FROM permission general
    LEFT JOIN permission almacenista ON almacenista.permission_description = 'Almacenista'
                                     AND almacenista.deletion_date IS NULL
    LEFT JOIN entity_permission referencia ON referencia.id_permission = almacenista.id_permission
                                            AND referencia.entity_name = 'warehouse_voucher'
                                            AND referencia.deletion_date IS NULL
    WHERE general.permission_description = 'Gerente Comercial' AND general.deletion_date IS NULL
    ON CONFLICT (id_permission, entity_name) DO NOTHING;
END IF;
END $$;

COMMIT;
