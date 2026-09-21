-- Capacidad separada para ajustar existencias.
--
-- Por que: el ajuste es el unico movimiento de almacen sin documento detras y
-- sin tope. Puede crear existencia de la nada o destruirla por cualquier
-- cantidad, asi que es justo la operacion con la que se tapa un faltante.
-- Antes bastaba con el permiso de editar productos, el mismo que necesita
-- cualquiera que registre una entrada o una salida normal.
--
-- Los demas movimientos quedan acotados: una salida no puede exceder la
-- existencia, una entrada por compra viene de una factura, y las mermas exigen
-- motivo escrito.
--
-- Se concede a los roles que ya tienen responsabilidad de inventario, no a
-- todos: quien surte y despacha no necesita poder ajustar.
--
-- ON CONFLICT en vez de NOT EXISTS (deletion_date IS NULL): 20260828240000
-- da de baja logica TODA la tabla y la resiembra desde el registro de
-- modulos, que a este permiso solo lo concede a 2 de estos 4 roles. En un
-- reinicio del pod (se reaplican las 45 migraciones desde cero cada vez) la
-- fila de este rol ya quedo borrada logicamente por esa resiembra, y el
-- UNIQUE(id_permission, entity_name) no distingue borrado logico: un NOT
-- EXISTS que solo mira filas activas vuelve a intentar el INSERT y choca
-- contra la fila fantasma. Verificado en tyakxa-dev el 2026-09-01.
BEGIN;

-- Guardado con un chequeo de existencia de scope_create: esta migracion es
-- anterior a 20260914110000_equipos_y_alcance_por_accion.sql, que agrega esas
-- 4 columnas y suelta control_type mas adelante en la misma pasada. Sin este
-- guardado, la primera pasada completa contra un volumen nuevo tronaria aqui
-- con "column scope_create does not exist". En pasadas posteriores la
-- columna ya existe y el INSERT corre normal.
DO $$
BEGIN
IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'entity_permission' AND column_name = 'scope_create'
) THEN

INSERT INTO entity_permission (id_permission, entity_name, scope_create, scope_read, scope_update, scope_delete, menu_location, menu_order, created_by)
SELECT p.id_permission, 'inventory_adjustment', 0, 4, 0, 0, 'hidden', 999, 1
FROM permission p
WHERE p.permission_description IN ('Administrator', 'admin', 'Gerente', 'gerente_administrativo')
  AND p.deletion_date IS NULL
ON CONFLICT (id_permission, entity_name) DO NOTHING;

END IF;
END $$;

COMMIT;
